"""Helpers shared by the server-rendered member form pages (/join, /write, ...)."""

from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.config.settings import settings
from app.schemas.user import PASSWORD_MIN_LENGTH
from app.services.member_session import form_csrf_token, set_form_csrf_cookie
from app.services.nav_service import get_nav_context


templates = Jinja2Templates(directory="app/templates")

FORM_EXPIRED = "Your form expired. Please try again."
TOO_MANY_ATTEMPTS = "Too many attempts. Please wait a few minutes and try again."
SERVICE_UNAVAILABLE = "This is unavailable right now. Please try again shortly."


async def render_form_page(
    request: Request,
    template: str,
    title: str,
    *,
    values: dict[str, Any],
    status_code: int = 200,
    error: str | None = None,
    field_errors: dict[str, str] | None = None,
    **extra: Any,
):
    """Render a form page with a CSRF token. Never echoes passwords."""
    csrf_token = form_csrf_token(request)
    context = {
        **await get_nav_context(request),
        "app_name": settings.app_name,
        "page_title": title,
        "seo_title": title,
        "robots": "noindex, nofollow",
        "values": values,
        "error": error,
        "field_errors": field_errors or {},
        "password_min_length": PASSWORD_MIN_LENGTH,
        "csrf_token": csrf_token,
        **extra,
    }
    response = templates.TemplateResponse(request, template, context, status_code=status_code)
    set_form_csrf_cookie(response, csrf_token)
    return response


def field_errors(exc: ValidationError) -> dict[str, str]:
    """First readable error per field, for showing next to that field."""
    errors: dict[str, str] = {}
    for error in exc.errors():
        field = str(error["loc"][0]) if error["loc"] else "form"
        limits = error.get("ctx") or {}
        if error["type"] == "string_too_short":
            minimum = limits.get("min_length", 0)
            message = f"Must be at least {minimum} characters." if minimum > 1 else "This field is required."
        elif error["type"] == "string_too_long":
            message = f"Must be at most {limits.get('max_length')} characters."
        elif error["type"] == "too_long":
            message = f"Use at most {limits.get('max_length')}."
        else:
            message = str(error["msg"]).removeprefix("Value error, ")
        errors.setdefault(field, message)
    return errors


def site_url(request: Request) -> str:
    """Where emailed links point. Production uses SITE_URL only: the Host
    header comes from the visitor, so trusting it would let someone send a
    real link that points at their own site."""
    if settings.site_url:
        return settings.site_url.rstrip("/")
    return "" if settings.app_env == "production" else str(request.base_url).rstrip("/")


def safe_next(value: str) -> str:
    """Only same-site paths, so ?next= cannot send people to another site."""
    value = (value or "").strip()
    if value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return ""
