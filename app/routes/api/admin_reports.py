from fastapi import APIRouter, Depends

from app.schemas.admin import AdminRead
from app.schemas.report import ReportAction
from app.services.admin_csrf import verify_admin_csrf
from app.services.admin_permissions import require_article_writer
from app.services.report_service import ReportService


router = APIRouter(prefix="/api/admin", tags=["Admin reports"])


def get_report_service() -> ReportService:
    return ReportService()


@router.post("/reports/action")
async def act_on_reports(
    payload: ReportAction,
    admin: AdminRead = Depends(require_article_writer),
    _csrf: None = Depends(verify_admin_csrf),
    service: ReportService = Depends(get_report_service),
) -> dict[str, int]:
    """Hide the reported item or dismiss its reports. Closes every open report on it."""
    return {"closed": await service.act(payload, admin)}
