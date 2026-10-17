from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status

from app.schemas.admin import AdminRead
from app.services.admin_csrf import verify_admin_csrf
from app.services.admin_permissions import require_article_writer
from app.services.cover_upload_service import MAX_UPLOAD_BYTES, CoverError, save_cover_upload


router = APIRouter(prefix="/api/admin/covers", tags=["Admin Covers"])


@router.post("", status_code=http_status.HTTP_201_CREATED)
async def upload_cover(
    file: UploadFile = File(...),
    _admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
) -> dict[str, str]:
    """Store an image; the editor puts the returned URL in the cover field and saves."""
    try:
        return {"url": await save_cover_upload(await file.read(MAX_UPLOAD_BYTES + 1))}
    except CoverError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
