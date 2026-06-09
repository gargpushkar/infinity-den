from fastapi import HTTPException, Request
from fastapi import status as http_status

from app.config.settings import settings
from app.utils.security import SecurityError, create_csrf_token, verify_csrf_token


ADMIN_CSRF_COOKIE = "admin_csrf_token"
ADMIN_CSRF_HEADER = "x-csrf-token"


def issue_admin_csrf_token() -> str:
    return create_csrf_token(settings.auth_secret_key)


async def verify_admin_csrf(request: Request) -> None:
    header_token = request.headers.get(ADMIN_CSRF_HEADER, "").strip()
    cookie_token = request.cookies.get(ADMIN_CSRF_COOKIE, "").strip()

    if not header_token or not cookie_token or header_token != cookie_token:
        raise _forbidden()

    try:
        is_valid = verify_csrf_token(header_token, settings.auth_secret_key)
    except SecurityError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin CSRF protection is not configured.",
        ) from exc

    if not is_valid:
        raise _forbidden()


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_403_FORBIDDEN,
        detail="Admin CSRF token is invalid or missing.",
    )
