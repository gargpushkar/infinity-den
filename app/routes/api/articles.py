from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import status as http_status
from fastapi.responses import Response

from app.models.article import ArticleStatus
from app.schemas.article import (
    ArticleCreate,
    ArticleListResponse,
    ArticleQueryParams,
    ArticleRead,
    ArticleSortField,
    ArticleUpdate,
    SortDirection,
)
from app.schemas.admin import AdminRead
from app.services.admin_csrf import verify_admin_csrf
from app.services.admin_permissions import (
    require_article_writer,
    require_destructive_admin,
)
from app.services.article_service import (
    ArticleNotFoundError,
    ArticleService,
    ArticleSlugConflictError,
    get_article_service,
)


router = APIRouter(prefix="/api/articles", tags=["Articles"])


def get_articles_service() -> ArticleService:
    return get_article_service()


@router.get(
    "",
    response_model=ArticleListResponse,
    response_model_by_alias=False,
)
async def list_articles(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, ge=1, le=100),
    article_status: ArticleStatus | None = Query(default=None, alias="status"),
    category_id: str | None = Query(default=None, max_length=120),
    tag: str | None = Query(default=None, max_length=64),
    is_featured: bool | None = Query(default=None),
    author: str | None = Query(default=None, max_length=120),
    published_from: datetime | None = Query(default=None),
    published_to: datetime | None = Query(default=None),
    search: str | None = Query(default=None, min_length=2, max_length=120),
    sort_by: ArticleSortField = Query(default="published_at"),
    sort_direction: SortDirection = Query(default="desc"),
    article_service: ArticleService = Depends(get_articles_service),
) -> ArticleListResponse:
    if (
        published_from is not None
        and published_to is not None
        and published_from > published_to
    ):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="published_from must be before published_to.",
        )

    query = ArticleQueryParams(
        page=page,
        per_page=per_page,
        status=article_status,
        category_id=category_id,
        tag=tag,
        is_featured=is_featured,
        author=author,
        published_from=published_from,
        published_to=published_to,
        search=search,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )

    return await article_service.list_articles(query)


@router.post(
    "",
    response_model=ArticleRead,
    response_model_by_alias=False,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_article(
    payload: ArticleCreate,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    article_service: ArticleService = Depends(get_articles_service),
) -> ArticleRead:
    try:
        return await article_service.create_article(payload)
    except ArticleSlugConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="An article with this slug already exists.",
        ) from exc


@router.get(
    "/{article_identifier}",
    response_model=ArticleRead,
    response_model_by_alias=False,
)
async def get_article_detail(
    article_identifier: str = Path(min_length=3, max_length=180),
    article_service: ArticleService = Depends(get_articles_service),
) -> ArticleRead:
    article = await article_service.get_article_detail(article_identifier)
    if article is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Article was not found.",
        )

    return article


@router.patch(
    "/{article_id}",
    response_model=ArticleRead,
    response_model_by_alias=False,
)
async def update_article(
    article_id: str,
    payload: ArticleUpdate,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    article_service: ArticleService = Depends(get_articles_service),
) -> ArticleRead:
    try:
        return await article_service.update_article(article_id, payload)
    except ArticleNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Article was not found.",
        ) from exc
    except ArticleSlugConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="An article with this slug already exists.",
        ) from exc


@router.delete("/{article_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    _admin: AdminRead = Depends(require_destructive_admin),
    _csrf: None = Depends(verify_admin_csrf),
    article_service: ArticleService = Depends(get_articles_service),
) -> Response:
    was_deleted = await article_service.delete_article(article_id)
    if not was_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Article was not found.",
        )

    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
