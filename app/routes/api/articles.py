from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.article import ArticleCreate, ArticleRead
from app.services.article_service import (
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
