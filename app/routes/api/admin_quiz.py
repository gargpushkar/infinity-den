from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from fastapi.responses import Response

from app.schemas.admin import AdminRead
from app.schemas.quiz import QuizItemInput, QuizItemRead
from app.services.admin_csrf import verify_admin_csrf
from app.services.admin_permissions import require_article_writer, require_destructive_admin
from app.services.quiz_service import QuizArticleNotFoundError, QuizItemNotFoundError, QuizService


router = APIRouter(prefix="/api/admin/quiz-items", tags=["Admin Arcade"])


def get_quiz_service() -> QuizService:
    return QuizService()


@router.post("", response_model=QuizItemRead, response_model_by_alias=False, status_code=http_status.HTTP_201_CREATED)
async def create_quiz_item(
    payload: QuizItemInput,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    service: QuizService = Depends(get_quiz_service),
) -> QuizItemRead:
    try:
        return await service.create_item(payload)
    except QuizArticleNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.patch("/{item_id}", response_model=QuizItemRead, response_model_by_alias=False)
async def update_quiz_item(
    item_id: str,
    payload: QuizItemInput,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    service: QuizService = Depends(get_quiz_service),
) -> QuizItemRead:
    try:
        return await service.update_item(item_id, payload)
    except QuizArticleNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except QuizItemNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{item_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_quiz_item(
    item_id: str,
    _admin: AdminRead = Depends(require_destructive_admin),
    _csrf: None = Depends(verify_admin_csrf),
    service: QuizService = Depends(get_quiz_service),
) -> Response:
    if not await service.delete_item(item_id):
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Claim was not found.")
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
