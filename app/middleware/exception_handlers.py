import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.settings import settings


logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")

DEFAULT_ERROR_MESSAGE = "Something went wrong. Please try again shortly."
VALIDATION_ERROR_MESSAGE = "The request data could not be validated."


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    status_code = exc.status_code
    message = _safe_message(exc.detail, status_code)

    if status_code >= 500:
        logger.error("HTTP error %s at %s: %s", status_code, request.url.path, message)
    else:
        logger.info("HTTP error %s at %s: %s", status_code, request.url.path, message)

    return _error_response(
        request=request,
        status_code=status_code,
        message=message,
        error_type="http_error",
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.info("Validation error at %s: %s", request.url.path, exc.errors())
    validation_errors = _json_safe_validation_errors(exc.errors())

    return _error_response(
        request=request,
        status_code=422,
        message=VALIDATION_ERROR_MESSAGE,
        error_type="validation_error",
        errors=validation_errors if _wants_json(request) else None,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error at %s", request.url.path)

    return _error_response(
        request=request,
        status_code=500,
        message=DEFAULT_ERROR_MESSAGE,
        error_type="server_error",
    )


def _error_response(
    *,
    request: Request,
    status_code: int,
    message: str,
    error_type: str,
    headers: dict[str, str] | None = None,
    errors: list[dict[str, Any]] | None = None,
):
    if _wants_json(request):
        payload: dict[str, Any] = {
            "error": {
                "type": error_type,
                "status_code": status_code,
                "message": message,
            }
        }
        if errors:
            payload["error"]["details"] = errors
        return JSONResponse(payload, status_code=status_code, headers=headers)

    return templates.TemplateResponse(
        request,
        "pages/error.html",
        {
            "app_name": settings.app_name,
            "page_title": _status_phrase(status_code),
            "status_code": status_code,
            "error_title": _status_phrase(status_code),
            "error_message": message,
        },
        status_code=status_code,
        headers=headers,
    )


def _wants_json(request: Request) -> bool:
    accept_header = request.headers.get("accept", "")
    return request.url.path.startswith("/api") or (
        "application/json" in accept_header and "text/html" not in accept_header
    )


def _safe_message(detail: Any, status_code: int) -> str:
    if status_code >= 500:
        return DEFAULT_ERROR_MESSAGE
    if isinstance(detail, str) and detail:
        return detail
    return _status_phrase(status_code)


def _json_safe_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe_errors: list[dict[str, Any]] = []

    for error in errors:
        safe_error = dict(error)
        context = safe_error.get("ctx")
        if isinstance(context, dict):
            safe_error["ctx"] = {key: str(value) for key, value in context.items()}
        safe_errors.append(safe_error)

    return safe_errors


def _status_phrase(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Request Error"
