from typing import Any

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi import status as http_status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from app.routes.public.form_pages import (
    FORM_EXPIRED,
    TOO_MANY_ATTEMPTS,
    field_errors,
    render_form_page,
)
from app.schemas.question import ResponseInput
from app.services.member_article_service import parse_sources
from app.services.member_session import form_csrf_is_valid, get_current_member, unconfirmed_redirect
from app.services.question_page_service import (
    get_question_room_context,
    own_response_values,
    question_url,
)
from app.services.question_service import QuestionService, site_today
from app.utils.forms import read_form
from app.utils.rate_limit import member_response_limiter


router = APIRouter()

TEMPLATE = "pages/question_room.html"
SLUG = Path(min_length=3, max_length=120)
NOTICES = {
    "saved": "Your response is live.",
    "deleted": "Your response was removed.",
}


@router.get("/questions")
async def question_room(request: Request, notice: str = "", kind: str = ""):
    """`?kind=thought|answer|story|researched` shows only that kind of response."""
    return await _page(request, slug=None, kind=kind, notice=NOTICES.get(notice))


@router.get("/questions/{slug}")
async def question_page(request: Request, slug: str = SLUG, notice: str = "", kind: str = ""):
    return await _page(request, slug=slug, kind=kind, notice=NOTICES.get(notice))


@router.post("/questions/{slug}/respond")
async def respond(request: Request, slug: str = SLUG):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next={question_url(slug)}", status_code=303)
    if redirect := unconfirmed_redirect(member):
        return redirect

    form = await read_form(request)
    values = {"kind": form.get("kind", ""), "body": form.get("body", ""), "sources": form.get("sources", "")}

    if not form_csrf_is_valid(request, form):
        return await _page(request, slug=slug, values=values, error=FORM_EXPIRED, status_code=400)
    question = await QuestionService().get_live_question(slug, site_today())
    if question is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Question was not found.")
    if not member_response_limiter.allow(member.id):
        return await _page(request, slug=slug, values=values, error=TOO_MANY_ATTEMPTS, status_code=429)

    try:
        payload = ResponseInput(kind=values["kind"], body=values["body"], sources=parse_sources(values["sources"]))
    except ValidationError as exc:
        errors = field_errors(exc)
        # Rules that span fields (length per kind, sources) arrive without a field name.
        if "form" in errors:
            errors.setdefault("body", errors.pop("form"))
        return await _page(request, slug=slug, values=values, field_errors=errors, status_code=422)

    await QuestionService().save_response(question, member, payload)
    return RedirectResponse(f"{question_url(slug)}?notice=saved#your-response", status_code=303)


@router.post("/questions/{slug}/respond/delete")
async def delete_response(request: Request, slug: str = SLUG):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next={question_url(slug)}", status_code=303)

    form = await read_form(request)
    if not form_csrf_is_valid(request, form):
        return await _page(request, slug=slug, error=FORM_EXPIRED, status_code=400)

    question = await QuestionService().get_live_question(slug, site_today())
    if question is not None:
        await QuestionService().delete_response(question.id, member)
    return RedirectResponse(f"{question_url(slug)}?notice=deleted", status_code=303)


async def _page(
    request: Request,
    *,
    slug: str | None,
    kind: str = "",
    values: dict[str, Any] | None = None,
    status_code: int = 200,
    **extra: Any,
):
    try:
        member = await get_current_member(request)
        context = await get_question_room_context(slug=slug, member=member, kind=kind)
    except (RuntimeError, PyMongoError):
        member, context = None, {"question": None, "past_questions": [], "is_unavailable": True}

    if context is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Question was not found.")

    question = context.get("question")
    title = question["text"] if question and slug else "The Question Room"
    return await render_form_page(
        request,
        TEMPLATE,
        title,
        values=values if values is not None else own_response_values(context),
        status_code=status_code,
        signed_in=member is not None,
        member_can_act=bool(member and member.email_confirmed),
        robots="index, follow",
        seo_description=(question["intro"] or question["text"]) if question else "One thought-provoking question a day, answered by the community.",
        **context,
        **extra,
    )
