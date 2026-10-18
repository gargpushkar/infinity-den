from typing import Any

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi import status as http_status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from app.config.constants import DEBATE_SIDE_LABELS, RATING_DIMENSIONS
from app.routes.public.form_pages import FORM_EXPIRED, TOO_MANY_ATTEMPTS, field_errors, render_form_page
from app.schemas.debate import ArgumentInput, RatingInput, RebuttalInput, StanceAfterInput, StanceBeforeInput
from app.services.debate_page_service import (
    debate_url,
    get_debate_context,
    get_debates_context,
    own_argument_values,
)
from app.services.debate_rating_service import DebateRatingService
from app.services.debate_stance_service import DebateStanceService, StanceLockedError
from app.services.debate_service import DebateClosedError, DebateNotFoundError, DebateService, OwnArgumentError
from app.services.member_article_service import parse_sources
from app.services.member_session import form_csrf_is_valid, get_current_member, unconfirmed_redirect
from app.services.question_service import site_today
from app.utils.forms import read_form
from app.utils.rate_limit import (
    member_argument_limiter,
    member_rating_limiter,
    member_rebuttal_limiter,
    member_stance_limiter,
)


router = APIRouter()

SLUG = Path(min_length=3, max_length=120)
ARGUMENT_ID = Path(pattern=r"^[0-9a-f]{24}$")
NOTICES = {
    "saved": "Your argument is live.",
    "deleted": "Your argument was removed.",
}


@router.get("/debates")
async def debates_page(request: Request):
    try:
        context = await get_debates_context()
    except (RuntimeError, PyMongoError):
        context = {"open_debates": [], "closed_debates": [], "is_unavailable": True}
    return await render_form_page(
        request,
        "pages/debates.html",
        "The Debate Den",
        values={},
        robots="index, follow",
        seo_description="Motions argued for and against, with evidence. Judge the argument, not the side.",
        **context,
    )


@router.get("/debates/{slug}")
async def debate_page(request: Request, slug: str = SLUG, notice: str = "", side: str = "", edit: bool = False):
    """`?side=for|against` opens the argument form on that side; `?edit=1` opens it to edit yours."""
    return await _page(request, slug=slug, notice=NOTICES.get(notice), open_side=side if side in DEBATE_SIDE_LABELS else "", open_edit=edit)


@router.post("/debates/{slug}/argue")
async def argue(request: Request, slug: str = SLUG):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next={debate_url(slug)}", status_code=303)
    if redirect := unconfirmed_redirect(member):
        return redirect

    form = await read_form(request)
    values = {key: form.get(key, "") for key in ("side", "claim", "body", "sources")}

    if not form_csrf_is_valid(request, form):
        return await _page(request, slug=slug, values=values, error=FORM_EXPIRED, status_code=400)
    debate = await DebateService().get_published_debate(slug)
    if debate is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Debate was not found.")
    if not member_argument_limiter.allow(member.id):
        return await _page(request, slug=slug, values=values, error=TOO_MANY_ATTEMPTS, status_code=429)

    try:
        payload = ArgumentInput(
            side=values["side"], claim=values["claim"], body=values["body"], sources=parse_sources(values["sources"])
        )
    except ValidationError as exc:
        return await _page(request, slug=slug, values=values, field_errors=field_errors(exc), status_code=422)

    try:
        saved = await DebateService().save_argument(debate, member, payload, site_today())
    except DebateClosedError as exc:
        return await _page(request, slug=slug, values=values, error=str(exc), status_code=409)
    return RedirectResponse(f"{debate_url(slug)}?notice=saved#argument-{saved.id}", status_code=303)


@router.post("/debates/{slug}/argue/delete")
async def delete_argument(request: Request, slug: str = SLUG):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next={debate_url(slug)}", status_code=303)

    form = await read_form(request)
    if not form_csrf_is_valid(request, form):
        return await _page(request, slug=slug, error=FORM_EXPIRED, status_code=400)

    debate = await DebateService().get_published_debate(slug)
    if debate is not None:
        await DebateService().delete_argument(debate.id, member)
    return RedirectResponse(f"{debate_url(slug)}?notice=deleted", status_code=303)


@router.post("/debates/{slug}/arguments/{argument_id}/rebut")
async def rebut(request: Request, slug: str = SLUG, argument_id: str = ARGUMENT_ID):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next={debate_url(slug)}", status_code=303)
    if redirect := unconfirmed_redirect(member):
        return redirect

    form = await read_form(request)
    rebuttal = {"argument_id": argument_id, "body": form.get("body", "")}

    if not form_csrf_is_valid(request, form):
        return await _page(request, slug=slug, rebuttal={**rebuttal, "error": FORM_EXPIRED}, status_code=400)
    debate = await DebateService().get_published_debate(slug)
    if debate is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Debate was not found.")
    if not member_rebuttal_limiter.allow(member.id):
        return await _page(request, slug=slug, rebuttal={**rebuttal, "error": TOO_MANY_ATTEMPTS}, status_code=429)

    try:
        payload = RebuttalInput(body=rebuttal["body"])
    except ValidationError as exc:
        error = field_errors(exc).get("body", "Check your rebuttal.")
        return await _page(request, slug=slug, rebuttal={**rebuttal, "error": error}, status_code=422)

    try:
        saved = await DebateService().save_rebuttal(debate, argument_id, member, payload, site_today())
    except (DebateClosedError, DebateNotFoundError, OwnArgumentError) as exc:
        return await _page(request, slug=slug, rebuttal={**rebuttal, "error": str(exc)}, status_code=409)
    return RedirectResponse(f"{debate_url(slug)}#rebuttal-{saved.id}", status_code=303)


@router.post("/debates/{slug}/arguments/{argument_id}/rebut/delete")
async def delete_rebuttal(request: Request, slug: str = SLUG, argument_id: str = ARGUMENT_ID):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next={debate_url(slug)}", status_code=303)

    form = await read_form(request)
    if not form_csrf_is_valid(request, form):
        return await _page(request, slug=slug, rebuttal={"argument_id": argument_id, "body": "", "error": FORM_EXPIRED}, status_code=400)

    await DebateService().delete_rebuttal(argument_id, member)
    return RedirectResponse(f"{debate_url(slug)}#argument-{argument_id}", status_code=303)


@router.post("/debates/{slug}/arguments/{argument_id}/rate")
async def rate(request: Request, slug: str = SLUG, argument_id: str = ARGUMENT_ID):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next={debate_url(slug)}", status_code=303)
    if redirect := unconfirmed_redirect(member):
        return redirect

    form = await read_form(request)
    rating = {"argument_id": argument_id, "scores": {key: form.get(key, "") for key in RATING_DIMENSIONS}}

    if not form_csrf_is_valid(request, form):
        return await _page(request, slug=slug, rating={**rating, "error": FORM_EXPIRED}, status_code=400)
    debate = await DebateService().get_published_debate(slug)
    if debate is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Debate was not found.")
    if not member_rating_limiter.allow(member.id):
        return await _page(request, slug=slug, rating={**rating, "error": TOO_MANY_ATTEMPTS}, status_code=429)

    try:
        payload = RatingInput(**rating["scores"])
    except ValidationError:
        return await _page(request, slug=slug, rating={**rating, "error": "Choose a score from 1 to 5 for all three."}, status_code=422)

    try:
        await DebateRatingService().save_rating(debate, argument_id, member, payload, site_today())
    except (DebateClosedError, DebateNotFoundError, OwnArgumentError) as exc:
        return await _page(request, slug=slug, rating={**rating, "error": str(exc)}, status_code=409)
    return RedirectResponse(f"{debate_url(slug)}#argument-{argument_id}", status_code=303)


@router.post("/debates/{slug}/stance/{moment}")
async def save_stance(request: Request, slug: str = SLUG, moment: str = Path(pattern="^(before|after)$")):
    """Where the member stands before reading, or after reading (with an optional note)."""
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next={debate_url(slug)}", status_code=303)
    if redirect := unconfirmed_redirect(member):
        return redirect

    form = await read_form(request)
    stance = {"moment": moment, "stance": form.get("stance", ""), "note": form.get("note", "")}

    if not form_csrf_is_valid(request, form):
        return await _page(request, slug=slug, stance={**stance, "error": FORM_EXPIRED}, status_code=400)
    debate = await DebateService().get_published_debate(slug)
    if debate is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Debate was not found.")
    if not member_stance_limiter.allow(member.id):
        return await _page(request, slug=slug, stance={**stance, "error": TOO_MANY_ATTEMPTS}, status_code=429)

    try:
        if moment == "before":
            payload = StanceBeforeInput(stance=stance["stance"])
        else:
            payload = StanceAfterInput(stance=stance["stance"], note=stance["note"])
    except ValidationError as exc:
        errors = field_errors(exc)
        error = errors.get("stance") or errors.get("note", "Check your answer.")
        return await _page(request, slug=slug, stance={**stance, "error": error}, status_code=422)

    service = DebateStanceService()
    try:
        if moment == "before":
            await service.save_before(debate, member, payload, site_today())
        else:
            await service.save_after(debate, member, payload, site_today())
    except (DebateClosedError, StanceLockedError) as exc:
        return await _page(request, slug=slug, stance={**stance, "error": str(exc)}, status_code=409)
    return RedirectResponse(f"{debate_url(slug)}#stance-{moment}", status_code=303)


async def _page(
    request: Request,
    *,
    slug: str,
    values: dict[str, Any] | None = None,
    status_code: int = 200,
    open_side: str = "",
    open_edit: bool = False,
    **extra: Any,
):
    """Render the debate. `values` comes only from a submitted argument, so the form opens with them."""
    try:
        member = await get_current_member(request)
        context = await get_debate_context(slug=slug, member=member)
    except (RuntimeError, PyMongoError):
        raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail="The Debate Den is unavailable right now.")
    if context is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Debate was not found.")

    debate = context["debate"]
    return await render_form_page(
        request,
        "pages/debate.html",
        debate["motion"],
        values=values if values is not None else (own_argument_values(context) or {"side": open_side}),
        status_code=status_code,
        signed_in=member is not None,
        member_can_act=bool(member and member.email_confirmed),
        argue_open=bool(values is not None or open_side or open_edit),
        robots="index, follow",
        seo_description=debate["intro"] or f"Arguments for and against: {debate['motion']}",
        **context,
        **extra,
    )
