from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from app.config.constants import REPORT_REASONS
from app.routes.public.form_pages import FORM_EXPIRED, TOO_MANY_ATTEMPTS, field_errors, render_form_page
from app.schemas.report import ReportInput
from app.services.member_session import form_csrf_is_valid, get_current_member, unconfirmed_redirect
from app.services.report_service import OwnContentError, ReportService, ReportTargetNotFoundError
from app.utils.forms import read_form
from app.utils.rate_limit import member_report_limiter


router = APIRouter()

TEMPLATE = "pages/report.html"
TARGET_TYPES = ("article", "response", "comment")


@router.get("/report")
async def report_page(
    request: Request,
    type: str = Query(default="", max_length=20),
    id: str = Query(default="", max_length=40),
):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?{urlencode({'next': f'/report?type={type}&id={id}'})}", status_code=303)
    if redirect := unconfirmed_redirect(member):
        return redirect
    return await _page(request, member, {"target_type": type, "target_id": id, "reason": "", "detail": ""})


@router.post("/report")
async def submit_report(request: Request):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse("/login", status_code=303)
    if redirect := unconfirmed_redirect(member):
        return redirect

    form = await read_form(request)
    values = {key: form.get(key, "") for key in ("target_type", "target_id", "reason", "detail")}
    if not form_csrf_is_valid(request, form):
        return await _page(request, member, values, error=FORM_EXPIRED, status_code=400)
    if not member_report_limiter.allow(member.id):
        return await _page(request, member, values, error=TOO_MANY_ATTEMPTS, status_code=429)

    try:
        payload = ReportInput(**values)
    except ValidationError as exc:
        errors = field_errors(exc)
        if "form" in errors:  # the "tell us what is wrong" rule spans fields
            errors.setdefault("detail", errors.pop("form"))
        return await _page(request, member, values, field_errors=errors, status_code=422)

    try:
        await ReportService().submit(member, payload)
    except (ReportTargetNotFoundError, OwnContentError) as exc:
        return await _page(request, member, values, error=str(exc), status_code=400)
    return await _page(request, member, values, is_done=True)


async def _page(request: Request, member, values: dict[str, str], *, status_code: int = 200, **extra):
    target = None
    if values["target_type"] in TARGET_TYPES and len(values["target_id"]) == 24:
        target = await ReportService().target(values["target_type"], values["target_id"])
    if target is not None and not target["is_visible"]:
        target = None
    return await render_form_page(
        request,
        TEMPLATE,
        "Report",
        values=values,
        status_code=status_code if target else 404,
        target=target,
        is_own=bool(target and target["owner_id"] == member.id),
        reasons=REPORT_REASONS,
        **extra,
    )
