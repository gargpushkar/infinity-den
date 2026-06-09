from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import status as http_status
from fastapi.responses import Response

from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryQueryParams,
    CategoryRead,
    CategorySortField,
    CategoryUpdate,
    SortDirection,
)
from app.schemas.admin import AdminRead
from app.services.admin_csrf import verify_admin_csrf
from app.services.admin_permissions import (
    require_content_manager,
    require_destructive_admin,
)
from app.services.category_service import (
    CategoryNotFoundError,
    CategoryService,
    CategorySlugConflictError,
    get_category_service,
)


router = APIRouter(prefix="/api/categories", tags=["Categories"])


def get_categories_service() -> CategoryService:
    return get_category_service()


@router.get(
    "",
    response_model=CategoryListResponse,
    response_model_by_alias=False,
)
async def list_categories(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, ge=1, le=100),
    search: str | None = Query(default=None, min_length=2, max_length=120),
    sort_by: CategorySortField = Query(default="name"),
    sort_direction: SortDirection = Query(default="asc"),
    category_service: CategoryService = Depends(get_categories_service),
) -> CategoryListResponse:
    query = CategoryQueryParams(
        page=page,
        per_page=per_page,
        search=search,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )

    return await category_service.list_categories(query)


@router.post(
    "",
    response_model=CategoryRead,
    response_model_by_alias=False,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_category(
    payload: CategoryCreate,
    _admin: AdminRead = Depends(require_content_manager),
    _csrf: None = Depends(verify_admin_csrf),
    category_service: CategoryService = Depends(get_categories_service),
) -> CategoryRead:
    try:
        return await category_service.create_category(payload)
    except CategorySlugConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="A category with this slug already exists.",
        ) from exc


@router.get(
    "/{category_identifier}",
    response_model=CategoryRead,
    response_model_by_alias=False,
)
async def get_category_detail(
    category_identifier: str = Path(min_length=2, max_length=120),
    category_service: CategoryService = Depends(get_categories_service),
) -> CategoryRead:
    category = await category_service.get_category_detail(category_identifier)
    if category is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Category was not found.",
        )

    return category


@router.patch(
    "/{category_id}",
    response_model=CategoryRead,
    response_model_by_alias=False,
)
async def update_category(
    category_id: str,
    payload: CategoryUpdate,
    _admin: AdminRead = Depends(require_content_manager),
    _csrf: None = Depends(verify_admin_csrf),
    category_service: CategoryService = Depends(get_categories_service),
) -> CategoryRead:
    try:
        return await category_service.update_category(category_id, payload)
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Category was not found.",
        ) from exc
    except CategorySlugConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="A category with this slug already exists.",
        ) from exc


@router.delete("/{category_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    _admin: AdminRead = Depends(require_destructive_admin),
    _csrf: None = Depends(verify_admin_csrf),
    category_service: CategoryService = Depends(get_categories_service),
) -> Response:
    was_deleted = await category_service.delete_category(category_id)
    if not was_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Category was not found.",
        )

    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
