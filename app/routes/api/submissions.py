from fastapi import APIRouter, Depends
from fastapi import status as http_status

from app.schemas.submission import (
    ArticleSubmissionCreate,
    ArticleSubmissionResponse,
)
from app.services.submission_service import SubmissionService, get_submission_service


router = APIRouter(prefix="/api/submissions", tags=["Submissions"])


def get_public_submission_service() -> SubmissionService:
    return get_submission_service()


@router.post(
    "",
    response_model=ArticleSubmissionResponse,
    response_model_by_alias=False,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_article_submission(
    payload: ArticleSubmissionCreate,
    submission_service: SubmissionService = Depends(get_public_submission_service),
) -> ArticleSubmissionResponse:
    submission = await submission_service.create_submission(payload)

    return ArticleSubmissionResponse(
        submission=submission,
        message="Article submission received.",
    )
