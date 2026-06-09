from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi import status as http_status
from fastapi.responses import Response

from app.schemas.admin import (
    AdminCreate,
    AdminListResponse,
    AdminPasswordUpdate,
    AdminRead,
    AdminRoleUpdate,
    AdminStatusUpdate,
)
from app.services.admin_auth_service import (
    AdminAlreadyExistsError,
    AdminAuthService,
    AdminLastAdminError,
    AdminNotFoundError,
    AdminSelfDeactivationError,
    get_admin_auth_service,
)
from app.services.admin_csrf import verify_admin_csrf
from app.services.admin_permissions import require_admin_manager


router = APIRouter(prefix="/api/admin/users", tags=["Admin Users"])


def get_admin_user_service() -> AdminAuthService:
    return get_admin_auth_service()


@router.get(
    "",
    response_model=AdminListResponse,
    response_model_by_alias=False,
)
async def list_admin_users(
    _admin: AdminRead = Depends(require_admin_manager),
    admin_service: AdminAuthService = Depends(get_admin_user_service),
) -> AdminListResponse:
    return await admin_service.list_admins()


@router.post(
    "",
    response_model=AdminRead,
    response_model_by_alias=False,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_admin_user(
    payload: AdminCreate,
    _admin: AdminRead = Depends(require_admin_manager),
    _csrf: None = Depends(verify_admin_csrf),
    admin_service: AdminAuthService = Depends(get_admin_user_service),
) -> AdminRead:
    try:
        return await admin_service.create_admin(payload)
    except AdminAlreadyExistsError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="An admin user with this username already exists.",
        ) from exc


@router.patch(
    "/{admin_id}/role",
    response_model=AdminRead,
    response_model_by_alias=False,
)
async def update_admin_user_role(
    payload: AdminRoleUpdate,
    admin_id: str = Path(min_length=12, max_length=64),
    _admin: AdminRead = Depends(require_admin_manager),
    _csrf: None = Depends(verify_admin_csrf),
    admin_service: AdminAuthService = Depends(get_admin_user_service),
) -> AdminRead:
    try:
        return await admin_service.update_admin_role(admin_id, payload.role)
    except AdminNotFoundError as exc:
        raise _not_found() from exc
    except AdminLastAdminError as exc:
        raise _conflict("At least one active admin account is required.") from exc


@router.patch("/{admin_id}/password", status_code=http_status.HTTP_204_NO_CONTENT)
async def update_admin_user_password(
    payload: AdminPasswordUpdate,
    admin_id: str = Path(min_length=12, max_length=64),
    _admin: AdminRead = Depends(require_admin_manager),
    _csrf: None = Depends(verify_admin_csrf),
    admin_service: AdminAuthService = Depends(get_admin_user_service),
) -> Response:
    try:
        await admin_service.update_admin_password(admin_id, payload.password)
    except AdminNotFoundError as exc:
        raise _not_found() from exc

    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{admin_id}/status",
    response_model=AdminRead,
    response_model_by_alias=False,
)
async def update_admin_user_status(
    payload: AdminStatusUpdate,
    admin_id: str = Path(min_length=12, max_length=64),
    current_admin: AdminRead = Depends(require_admin_manager),
    _csrf: None = Depends(verify_admin_csrf),
    admin_service: AdminAuthService = Depends(get_admin_user_service),
) -> AdminRead:
    try:
        return await admin_service.update_admin_status(
            admin_id,
            is_active=payload.is_active,
            acting_admin_id=current_admin.id,
        )
    except AdminNotFoundError as exc:
        raise _not_found() from exc
    except AdminLastAdminError as exc:
        raise _conflict("At least one active admin account is required.") from exc
    except AdminSelfDeactivationError as exc:
        raise _conflict("You cannot deactivate your own admin account.") from exc


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_404_NOT_FOUND,
        detail="Admin user was not found.",
    )


def _conflict(message: str) -> HTTPException:
    return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=message)
