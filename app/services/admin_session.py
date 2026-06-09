from fastapi import Depends, HTTPException, Request
from fastapi import status as http_status

from app.config.settings import settings
from app.schemas.admin import AdminRead
from app.services.admin_auth_service import AdminAuthService, get_admin_auth_service
from app.utils.security import TokenValidationError, decode_access_token


ADMIN_AUTH_COOKIE = "admin_access_token"


def get_admin_session_service() -> AdminAuthService:
    return get_admin_auth_service()


async def get_current_admin(
    request: Request,
    admin_service: AdminAuthService = Depends(get_admin_session_service),
) -> AdminRead:
    token = _extract_access_token(request)
    if token is None:
        raise _unauthorized()

    try:
        payload = decode_access_token(token, settings.auth_secret_key)
    except TokenValidationError as exc:
        raise _unauthorized() from exc

    admin_id = payload.get("sub")
    if not isinstance(admin_id, str):
        raise _unauthorized()

    admin = await admin_service.get_admin_by_id(admin_id)
    if admin is None:
        raise _unauthorized()

    return admin


async def get_optional_current_admin(
    request: Request,
    admin_service: AdminAuthService = Depends(get_admin_session_service),
) -> AdminRead | None:
    try:
        return await get_current_admin(request, admin_service)
    except HTTPException:
        return None


def _extract_access_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        return token or None

    cookie_token = request.cookies.get(ADMIN_AUTH_COOKIE)
    if cookie_token:
        return cookie_token.strip()

    return None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_401_UNAUTHORIZED,
        detail="Admin authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
