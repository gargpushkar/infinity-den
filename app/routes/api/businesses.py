from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import status as http_status
from fastapi.responses import Response

from app.schemas.admin import AdminRead
from app.schemas.business import (
    BusinessCreate,
    BusinessListResponse,
    BusinessQueryParams,
    BusinessRead,
    BusinessSortField,
    BusinessUpdate,
    SortDirection,
)
from app.services.admin_csrf import verify_admin_csrf
from app.services.admin_permissions import (
    require_content_manager,
    require_destructive_admin,
)
from app.services.business_service import (
    BusinessNotFoundError,
    BusinessService,
    BusinessSlugConflictError,
    get_business_service,
)


router = APIRouter(prefix="/api/businesses", tags=["Businesses"])


def get_businesses_service() -> BusinessService:
    return get_business_service()


@router.get(
    "",
    response_model=BusinessListResponse,
    response_model_by_alias=False,
)
async def list_businesses(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, ge=1, le=100),
    search: str | None = Query(default=None, min_length=2, max_length=120),
    category_id: str | None = Query(default=None, max_length=120),
    is_featured: bool | None = Query(default=None),
    sort_by: BusinessSortField = Query(default="sort_order"),
    sort_direction: SortDirection = Query(default="asc"),
    business_service: BusinessService = Depends(get_businesses_service),
) -> BusinessListResponse:
    query = BusinessQueryParams(
        page=page,
        per_page=per_page,
        search=search,
        category_id=category_id,
        is_featured=is_featured,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )

    return await business_service.list_businesses(query)


@router.post(
    "",
    response_model=BusinessRead,
    response_model_by_alias=False,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_business(
    payload: BusinessCreate,
    _admin: AdminRead = Depends(require_content_manager),
    _csrf: None = Depends(verify_admin_csrf),
    business_service: BusinessService = Depends(get_businesses_service),
) -> BusinessRead:
    try:
        return await business_service.create_business(payload)
    except BusinessSlugConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="A business with this slug already exists.",
        ) from exc


@router.get(
    "/{business_identifier}",
    response_model=BusinessRead,
    response_model_by_alias=False,
)
async def get_business_detail(
    business_identifier: str = Path(min_length=2, max_length=120),
    business_service: BusinessService = Depends(get_businesses_service),
) -> BusinessRead:
    business = await business_service.get_business_detail(business_identifier)
    if business is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Business was not found.",
        )

    return business


@router.patch(
    "/{business_id}",
    response_model=BusinessRead,
    response_model_by_alias=False,
)
async def update_business(
    business_id: str,
    payload: BusinessUpdate,
    _admin: AdminRead = Depends(require_content_manager),
    _csrf: None = Depends(verify_admin_csrf),
    business_service: BusinessService = Depends(get_businesses_service),
) -> BusinessRead:
    try:
        return await business_service.update_business(business_id, payload)
    except BusinessNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Business was not found.",
        ) from exc
    except BusinessSlugConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="A business with this slug already exists.",
        ) from exc


@router.delete("/{business_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_business(
    business_id: str,
    _admin: AdminRead = Depends(require_destructive_admin),
    _csrf: None = Depends(verify_admin_csrf),
    business_service: BusinessService = Depends(get_businesses_service),
) -> Response:
    was_deleted = await business_service.delete_business(business_id)
    if not was_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Business was not found.",
        )

    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
