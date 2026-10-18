from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from fastapi.responses import Response

from app.schemas.admin import AdminRead
from app.schemas.debate import AdminArgumentUpdate, AdminRebuttalUpdate, ArgumentRead, DebateInput, DebateRead, RebuttalRead
from app.services.admin_csrf import verify_admin_csrf
from app.services.admin_permissions import require_article_writer, require_destructive_admin
from app.services.debate_service import DebateNotFoundError, DebateService


router = APIRouter(prefix="/api/admin", tags=["Admin Debate Den"])


def get_debate_service() -> DebateService:
    return DebateService()


@router.post("/debates", response_model=DebateRead, response_model_by_alias=False, status_code=http_status.HTTP_201_CREATED)
async def create_debate(
    payload: DebateInput,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    service: DebateService = Depends(get_debate_service),
) -> DebateRead:
    return await service.create_debate(payload)


@router.patch("/debates/{debate_id}", response_model=DebateRead, response_model_by_alias=False)
async def update_debate(
    debate_id: str,
    payload: DebateInput,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    service: DebateService = Depends(get_debate_service),
) -> DebateRead:
    try:
        return await service.update_debate(debate_id, payload)
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/debates/{debate_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_debate(
    debate_id: str,
    _admin: AdminRead = Depends(require_destructive_admin),
    _csrf: None = Depends(verify_admin_csrf),
    service: DebateService = Depends(get_debate_service),
) -> Response:
    if not await service.delete_debate(debate_id):
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Debate was not found.")
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.patch("/arguments/{argument_id}", response_model=ArgumentRead, response_model_by_alias=False)
async def moderate_argument(
    argument_id: str,
    payload: AdminArgumentUpdate,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    service: DebateService = Depends(get_debate_service),
) -> ArgumentRead:
    """Feature an argument, or hide / restore it."""
    try:
        return await service.moderate_argument(argument_id, payload)
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/rebuttals/{rebuttal_id}", response_model=RebuttalRead, response_model_by_alias=False)
async def moderate_rebuttal(
    rebuttal_id: str,
    payload: AdminRebuttalUpdate,
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    service: DebateService = Depends(get_debate_service),
) -> RebuttalRead:
    """Hide or restore a rebuttal."""
    try:
        return await service.moderate_rebuttal(rebuttal_id, payload)
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
