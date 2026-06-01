from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
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
    status: ArticleStatus | None = Query(default=None),
    category_id: str | None = Query(default=None, max_length=120),
    tag: str | None = Query(default=None, max_length=64),
    search: str | None = Query(default=None, min_length=2, max_length=120),
    sort_by: ArticleSortField = Query(default="published_at"),
    sort_direction: SortDirection = Query(default="desc"),
    article_service: ArticleService = Depends(get_articles_service),
) -> ArticleListResponse:
    query = ArticleQueryParams(
        page=page,
        per_page=per_page,
        status=status,
        category_id=category_id,
        tag=tag,
        search=search,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )

    return await article_service.list_articles(query)


@router.post(
    "",
    response_model=ArticleRead,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
async def create_article(
    payload: ArticleCreate,
    article_service: ArticleService = Depends(get_articles_service),
) -> ArticleRead:
    try:
        return await article_service.create_article(payload)
    except ArticleSlugConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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
            status_code=status.HTTP_404_NOT_FOUND,
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
    article_service: ArticleService = Depends(get_articles_service),
) -> ArticleRead:
    try:
        return await article_service.update_article(article_id, payload)
    except ArticleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article was not found.",
        ) from exc
    except ArticleSlugConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An article with this slug already exists.",
        ) from exc


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    article_service: ArticleService = Depends(get_articles_service),
) -> Response:
    was_deleted = await article_service.delete_article(article_id)
    if not was_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article was not found.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
