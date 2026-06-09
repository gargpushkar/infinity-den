from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status

from app.config.constants import ARTICLE_STATUS_DRAFT, ARTICLE_STATUS_PUBLISHED
from app.schemas.admin import AdminArticleFeatureUpdate, AdminRead
from app.schemas.article import ArticleRead, ArticleUpdate
from app.schemas.submission import ArticleSubmissionRead, ArticleSubmissionUpdate
from app.services.admin_session import get_current_admin
from app.services.article_service import (
    ArticleNotFoundError,
    ArticleService,
    get_article_service,
)
from app.services.submission_service import (
    SubmissionNotFoundError,
    SubmissionService,
    get_submission_service,
)


router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])


def get_admin_article_service() -> ArticleService:
    return get_article_service()


def get_admin_submission_service() -> SubmissionService:
    return get_submission_service()


@router.patch(
    "/articles/{article_id}/publish",
    response_model=ArticleRead,
    response_model_by_alias=False,
)
async def publish_article(
    article_id: str,
    _admin: AdminRead = Depends(get_current_admin),
    article_service: ArticleService = Depends(get_admin_article_service),
) -> ArticleRead:
    try:
        return await article_service.update_article(
            article_id,
            ArticleUpdate(
                status=ARTICLE_STATUS_PUBLISHED,
                published_at=datetime.now(timezone.utc),
            ),
        )
    except ArticleNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Article was not found.",
        ) from exc


@router.patch(
    "/articles/{article_id}/draft",
    response_model=ArticleRead,
    response_model_by_alias=False,
)
async def move_article_to_draft(
    article_id: str,
    _admin: AdminRead = Depends(get_current_admin),
    article_service: ArticleService = Depends(get_admin_article_service),
) -> ArticleRead:
    try:
        return await article_service.update_article(
            article_id,
            ArticleUpdate(status=ARTICLE_STATUS_DRAFT, published_at=None),
        )
    except ArticleNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Article was not found.",
        ) from exc


@router.patch(
    "/articles/{article_id}/feature",
    response_model=ArticleRead,
    response_model_by_alias=False,
)
async def update_article_feature_state(
    article_id: str,
    payload: AdminArticleFeatureUpdate,
    _admin: AdminRead = Depends(get_current_admin),
    article_service: ArticleService = Depends(get_admin_article_service),
) -> ArticleRead:
    try:
        return await article_service.update_article(
            article_id,
            ArticleUpdate(is_featured=payload.is_featured),
        )
    except ArticleNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Article was not found.",
        ) from exc


@router.patch(
    "/submissions/{submission_id}/status",
    response_model=ArticleSubmissionRead,
    response_model_by_alias=False,
)
async def update_submission_status(
    submission_id: str,
    payload: ArticleSubmissionUpdate,
    _admin: AdminRead = Depends(get_current_admin),
    submission_service: SubmissionService = Depends(get_admin_submission_service),
) -> ArticleSubmissionRead:
    try:
        return await submission_service.update_submission_status(
            submission_id,
            payload.status,
        )
    except SubmissionNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Submission was not found.",
        ) from exc
