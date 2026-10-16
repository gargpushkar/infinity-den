from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from fastapi.responses import Response

from app.schemas.admin import AdminRead
from app.schemas.question import AdminResponseUpdate, QuestionInput, QuestionRead, ResponseRead
from app.services.admin_csrf import verify_admin_csrf
from app.services.admin_permissions import require_article_writer, require_destructive_admin
from app.services.question_service import (
    QuestionDateTakenError,
    QuestionNotFoundError,
    QuestionService,
)


router = APIRouter(prefix="/api/admin", tags=["Admin Question Room"])


def get_question_service() -> QuestionService:
    return QuestionService()


@router.post("/questions", response_model=QuestionRead, response_model_by_alias=False, status_code=http_status.HTTP_201_CREATED)
async def create_question(
    payload: QuestionInput,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    service: QuestionService = Depends(get_question_service),
) -> QuestionRead:
    try:
        return await service.create_question(payload)
    except QuestionDateTakenError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/questions/{question_id}", response_model=QuestionRead, response_model_by_alias=False)
async def update_question(
    question_id: str,
    payload: QuestionInput,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    service: QuestionService = Depends(get_question_service),
) -> QuestionRead:
    try:
        return await service.update_question(question_id, payload)
    except QuestionDateTakenError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/questions/{question_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: str,
    _admin: AdminRead = Depends(require_destructive_admin),
    _csrf: None = Depends(verify_admin_csrf),
    service: QuestionService = Depends(get_question_service),
) -> Response:
    if not await service.delete_question(question_id):
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Question was not found.")
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.patch("/responses/{response_id}", response_model=ResponseRead, response_model_by_alias=False)
async def moderate_response(
    response_id: str,
    payload: AdminResponseUpdate,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    service: QuestionService = Depends(get_question_service),
) -> ResponseRead:
    """Feature a response, or hide / restore it."""
    try:
        return await service.moderate_response(response_id, payload)
    except QuestionNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
