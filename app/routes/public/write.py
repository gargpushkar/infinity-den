from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from app.config.constants import (
    ARTICLE_FORMAT_EXPERIENCE,
    ARTICLE_FORMAT_LABELS,
    HUMAN_LIBRARY_PROMPTS,
)
from app.database.mongodb import get_database
from app.routes.public.form_pages import (
    FORM_EXPIRED,
    SERVICE_UNAVAILABLE,
    TOO_MANY_ATTEMPTS,
    field_errors,
    render_form_page,
)
from app.schemas.article import ArticleRead, MemberPieceInput
from app.schemas.user import MemberRead
from app.services.member_article_service import (
    MEMBER_EDITABLE_STATUSES,
    MemberArticleService,
    PieceInvalidError,
    PieceLockedError,
    PieceNotFoundError,
    parse_sources,
    sources_text,
)
from app.services.member_session import form_csrf_is_valid, get_current_member
from app.services.nav_service import get_rooms
from app.utils.forms import read_form
from app.utils.rate_limit import member_save_limiter, member_submit_limiter


router = APIRouter()

TEMPLATE = "pages/member_write.html"
SAVED_NOTICES = {
    "draft": "Draft saved. Only you can see it.",
    "submitted": "Submitted for review. An editor will publish it or send it back with a note.",
}
TEXT_FIELDS = ("title", "excerpt", "content", "category_id", "article_format", "tags", "sources")


@router.get("/write")
async def new_piece(request: Request, format: str = "", prompt: int | None = None):
    member = await get_current_member(request)
    if member is None:
        return _login_redirect(request)

    prompt_text = HUMAN_LIBRARY_PROMPTS[prompt] if prompt is not None and 0 <= prompt < len(HUMAN_LIBRARY_PROMPTS) else ""
    values = {
        "article_format": format if format in ARTICLE_FORMAT_LABELS else ARTICLE_FORMAT_EXPERIENCE,
        "category_id": "personal-stories" if prompt_text else "",
    }
    return await _page(request, values=values, prompt=prompt_text)


@router.post("/write")
async def create_piece(request: Request):
    return await _save(request, article_id=None)


@router.get("/write/{article_id}")
async def edit_piece(request: Request, article_id: str, saved: str = ""):
    member = await get_current_member(request)
    if member is None:
        return _login_redirect(request)

    try:
        piece = await MemberArticleService().get_own(member, article_id)
    except PieceNotFoundError:
        return await _page(request, values={}, piece=None, error="That piece was not found.", status_code=404)

    return await _page(request, values=_piece_values(piece), piece=piece, notice=SAVED_NOTICES.get(saved))


@router.post("/write/{article_id}")
async def update_piece(request: Request, article_id: str):
    return await _save(request, article_id=article_id)


async def _save(request: Request, *, article_id: str | None):
    member = await get_current_member(request)
    if member is None:
        return _login_redirect(request)

    form = await read_form(request)
    values: dict[str, Any] = {name: form.get(name, "") for name in TEXT_FIELDS}
    values["is_speculative"] = form.get("is_speculative") == "true"
    submit = form.get("action") == "submit"
    piece = await _own_piece_or_none(member, article_id)

    if not form_csrf_is_valid(request, form):
        return await _page(request, values=values, piece=piece, error=FORM_EXPIRED, status_code=400)
    limiter = member_submit_limiter if submit else member_save_limiter
    if not limiter.allow(member.id):
        return await _page(request, values=values, piece=piece, error=TOO_MANY_ATTEMPTS, status_code=429)

    try:
        payload = MemberPieceInput(
            **{name: values[name] for name in ("title", "excerpt", "content", "category_id", "article_format")},
            tags=[tag for tag in values["tags"].split(",")],
            sources=parse_sources(values["sources"]),
            is_speculative=values["is_speculative"],
        )
        saved = await MemberArticleService().save(member, payload, submit=submit, article_id=article_id)
    except ValidationError as exc:
        return await _page(request, values=values, piece=piece, field_errors=field_errors(exc), status_code=422)
    except PieceInvalidError as exc:
        return await _page(request, values=values, piece=piece, field_errors={exc.field: str(exc)}, status_code=422)
    except PieceNotFoundError:
        return await _page(request, values=values, piece=None, error="That piece was not found.", status_code=404)
    except PieceLockedError as exc:
        return await _page(request, values=values, piece=piece, error=str(exc), status_code=409)
    except (RuntimeError, PyMongoError):
        return await _page(request, values=values, piece=piece, error=SERVICE_UNAVAILABLE, status_code=503)

    outcome = "submitted" if submit else "draft"
    return RedirectResponse(f"/write/{saved.id}?saved={outcome}", status_code=303)


async def _page(request: Request, *, values: dict[str, Any], piece: ArticleRead | None = None, prompt: str = "", notice: str | None = None, **extra: Any):
    try:
        rooms = await get_rooms(get_database())
    except (RuntimeError, PyMongoError):
        rooms = []

    return await render_form_page(
        request,
        TEMPLATE,
        "Edit your piece" if piece else "Write",
        values=values,
        piece=piece,
        rooms=rooms,
        formats=ARTICLE_FORMAT_LABELS,
        prompt=prompt,
        notice=notice,
        is_locked=bool(piece and piece.status not in MEMBER_EDITABLE_STATUSES),
        **extra,
    )


async def _own_piece_or_none(member: MemberRead, article_id: str | None) -> ArticleRead | None:
    if article_id is None:
        return None
    try:
        return await MemberArticleService().get_own(member, article_id)
    except (PieceNotFoundError, RuntimeError, PyMongoError):
        return None


def _piece_values(piece: ArticleRead) -> dict[str, Any]:
    return {
        "title": piece.title,
        "excerpt": piece.excerpt,
        "content": piece.content,
        "category_id": piece.category_id or "",
        "article_format": piece.article_format,
        "tags": ", ".join(piece.tags),
        "sources": sources_text(piece.sources),
        "is_speculative": piece.is_speculative,
    }


def _login_redirect(request: Request) -> RedirectResponse:
    target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    return RedirectResponse(f"/login?next={quote(target, safe='')}", status_code=303)
