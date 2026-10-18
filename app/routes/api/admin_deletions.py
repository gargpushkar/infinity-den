from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from fastapi.responses import JSONResponse, Response
from starlette.background import BackgroundTask

from app.schemas.admin import AdminDeletionInput, AdminRead
from app.services.account_deletion_service import AccountDeletionService, parse_emails, send_deleted_emails
from app.services.admin_csrf import verify_admin_csrf
from app.services.admin_permissions import require_destructive_admin


router = APIRouter(prefix="/api/admin/deletions", tags=["Admin Deletions"])


@router.post("/preview")
async def preview_deletion(
    payload: AdminDeletionInput,
    _admin: AdminRead = Depends(require_destructive_admin),
    _csrf: None = Depends(verify_admin_csrf),
) -> dict:
    """What deleting these addresses would remove. Deletes nothing."""
    return {"rows": await AccountDeletionService().preview(parse_emails(payload.emails))}


@router.post("/delete")
async def delete_accounts(
    payload: AdminDeletionInput,
    admin: AdminRead = Depends(require_destructive_admin),
    _csrf: None = Depends(verify_admin_csrf),
) -> JSONResponse:
    results = await AccountDeletionService().delete_by_emails(parse_emails(payload.emails), admin.username)
    # Members who asked get a confirmation, sent after the reply so a big batch doesn't wait on email.
    public = [{key: r[key] for key in ("email", "deleted") if key in r} for r in results]
    return JSONResponse({"results": public}, background=BackgroundTask(send_deleted_emails, results))


@router.post("/{request_id}/cancel", status_code=http_status.HTTP_204_NO_CONTENT)
async def cancel_deletion_request(
    request_id: str,
    admin: AdminRead = Depends(require_destructive_admin),
    _csrf: None = Depends(verify_admin_csrf),
) -> Response:
    if not await AccountDeletionService().cancel(request_id, admin.username):
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="That request was not found.")
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
