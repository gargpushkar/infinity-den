from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.article import ArticleCreate, ArticleRead, ArticleUpdate
from app.services.article_service import (
    ArticleNotFoundError,
    ArticleService,
    ArticleSlugConflictError,
    get_article_service,
)


router = APIRouter(prefix="/api/articles", tags=["Articles"])


def get_articles_service() -> ArticleService:
    return get_article_service()


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
