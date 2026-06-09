from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import status as http_status
from fastapi.responses import Response

from app.schemas.tag import (
    SortDirection,
    TagCreate,
    TagListResponse,
    TagQueryParams,
    TagRead,
    TagSortField,
    TagUpdate,
)
from app.services.tag_service import (
    TagNotFoundError,
    TagService,
    TagSlugConflictError,
    get_tag_service,
)


router = APIRouter(prefix="/api/tags", tags=["Tags"])


def get_tags_service() -> TagService:
    return get_tag_service()


@router.get(
    "",
    response_model=TagListResponse,
    response_model_by_alias=False,
)
async def list_tags(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, ge=1, le=100),
    search: str | None = Query(default=None, min_length=2, max_length=64),
    sort_by: TagSortField = Query(default="name"),
    sort_direction: SortDirection = Query(default="asc"),
    tag_service: TagService = Depends(get_tags_service),
) -> TagListResponse:
    query = TagQueryParams(
        page=page,
        per_page=per_page,
        search=search,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )

    return await tag_service.list_tags(query)


@router.post(
    "",
    response_model=TagRead,
    response_model_by_alias=False,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_tag(
    payload: TagCreate,
    tag_service: TagService = Depends(get_tags_service),
) -> TagRead:
    try:
        return await tag_service.create_tag(payload)
    except TagSlugConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="A tag with this slug already exists.",
        ) from exc


@router.get(
    "/{tag_identifier}",
    response_model=TagRead,
    response_model_by_alias=False,
)
async def get_tag_detail(
    tag_identifier: str = Path(min_length=2, max_length=64),
    tag_service: TagService = Depends(get_tags_service),
) -> TagRead:
    tag = await tag_service.get_tag_detail(tag_identifier)
    if tag is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Tag was not found.",
        )

    return tag


@router.patch(
    "/{tag_id}",
    response_model=TagRead,
    response_model_by_alias=False,
)
async def update_tag(
    tag_id: str,
    payload: TagUpdate,
    tag_service: TagService = Depends(get_tags_service),
) -> TagRead:
    try:
        return await tag_service.update_tag(tag_id, payload)
    except TagNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Tag was not found.",
        ) from exc
    except TagSlugConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="A tag with this slug already exists.",
        ) from exc


@router.delete("/{tag_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: str,
    tag_service: TagService = Depends(get_tags_service),
) -> Response:
    was_deleted = await tag_service.delete_tag(tag_id)
    if not was_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Tag was not found.",
        )

    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
