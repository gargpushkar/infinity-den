from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi import status as http_status

from app.config.settings import settings
from app.schemas.admin import AdminLoginRequest, AdminRead, AdminTokenResponse
from app.services.admin_auth_service import (
    AdminAuthService,
    AdminInvalidCredentialsError,
    get_admin_auth_service,
)
from app.services.admin_session import ADMIN_AUTH_COOKIE, get_current_admin
from app.utils.security import SecurityError


router = APIRouter(prefix="/api/admin", tags=["Admin Authentication"])


def get_admin_service() -> AdminAuthService:
    return get_admin_auth_service()


@router.post(
    "/login",
    response_model=AdminTokenResponse,
    response_model_by_alias=False,
)
async def login_admin(
    payload: AdminLoginRequest,
    response: Response,
    admin_service: AdminAuthService = Depends(get_admin_service),
) -> AdminTokenResponse:
    try:
        admin = await admin_service.authenticate_admin(
            username=payload.username,
            password=payload.password,
        )
        access_token = admin_service.create_login_token(admin)
    except AdminInvalidCredentialsError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except SecurityError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication is not configured.",
        ) from exc

    expires_in = settings.auth_token_expire_minutes * 60
    response.set_cookie(
        ADMIN_AUTH_COOKIE,
        access_token,
        max_age=expires_in,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )

    return AdminTokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        admin=admin,
    )


@router.post("/logout", status_code=http_status.HTTP_204_NO_CONTENT)
async def logout_admin(response: Response) -> Response:
    response.delete_cookie(ADMIN_AUTH_COOKIE)
    response.status_code = http_status.HTTP_204_NO_CONTENT
    return response


@router.get(
    "/me",
    response_model=AdminRead,
    response_model_by_alias=False,
)
async def get_authenticated_admin(
    admin: AdminRead = Depends(get_current_admin),
) -> AdminRead:
    return admin
