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
from app.services.cover_upload_service import (
    MAX_UPLOAD_BYTES,
    UPLOADED_COVER,
    CoverError,
    cover_link,
    discard_unused_cover,
    save_cover_upload,
)
from app.services.member_session import form_csrf_is_valid, get_current_member, unconfirmed_redirect
from app.services.nav_service import get_rooms
from app.utils.covers import cover_url
from app.utils.forms import read_upload_form
from app.utils.rate_limit import member_save_limiter, member_submit_limiter


router = APIRouter()

TEMPLATE = "pages/member_write.html"
SAVED_NOTICES = {
    "draft": "Draft saved. Only you can see it.",
    "submitted": "Submitted for review. An editor will publish it or send it back with a note.",
}
TEXT_FIELDS = ("title", "excerpt", "content", "category_id", "article_format", "tags", "sources", "cover_url")
CHOOSE_AGAIN = "Choose your image again; files aren't kept when the form has a problem."


@router.get("/write")
async def new_piece(request: Request, format: str = "", prompt: int | None = None):
    member = await get_current_member(request)
    if member is None:
        return _login_redirect(request)
    if redirect := unconfirmed_redirect(member):
        return redirect

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
    if redirect := unconfirmed_redirect(member):
        return redirect

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
    if redirect := unconfirmed_redirect(member):
        return redirect

    form, upload = await read_upload_form(request, "cover_file", MAX_UPLOAD_BYTES)
    values: dict[str, Any] = {name: form.get(name, "") for name in TEXT_FIELDS}
    values["is_speculative"] = form.get("is_speculative") == "true"
    values["cover_remove"] = form.get("cover_remove") == "true"
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
    except ValidationError as exc:
        errors = field_errors(exc) | ({"cover": CHOOSE_AGAIN} if upload else {})
        return await _page(request, values=values, piece=piece, field_errors=errors, status_code=422)

    # The image is stored only once the rest of the form is valid.
    current_cover = piece.cover_image if piece else None
    try:
        cover = await _chosen_cover(current_cover, values, upload)
    except CoverError as exc:
        return await _page(request, values=values, piece=piece, field_errors={"cover": str(exc)}, status_code=422)

    saved = None
    try:
        saved = await MemberArticleService().save(member, payload, submit=submit, article_id=article_id, cover_image=cover)
    except PieceInvalidError as exc:
        errors = {exc.field: str(exc)} | ({"cover": CHOOSE_AGAIN} if upload else {})
        return await _page(request, values=values, piece=piece, field_errors=errors, status_code=422)
    except PieceNotFoundError:
        return await _page(request, values=values, piece=None, error="That piece was not found.", status_code=404)
    except PieceLockedError as exc:
        return await _page(request, values=values, piece=piece, error=str(exc), status_code=409)
    except (RuntimeError, PyMongoError):
        return await _page(request, values=values, piece=piece, error=SERVICE_UNAVAILABLE, status_code=503)
    finally:
        if saved is None and cover != current_cover:
            await _discard_quietly(cover)  # the new upload is not used by any piece

    outcome = "submitted" if submit else "draft"
    return RedirectResponse(f"/write/{saved.id}?saved={outcome}", status_code=303)


async def _chosen_cover(current: str | None, values: dict[str, Any], upload: bytes | None) -> str | None:
    """A new upload wins, then "remove", then a pasted link. Otherwise an
    uploaded cover stays, and a link the member cleared is dropped."""
    if upload:
        return await save_cover_upload(upload)
    if values["cover_remove"]:
        return None
    if values["cover_url"].strip():
        return cover_link(values["cover_url"])
    return current if current and UPLOADED_COVER.match(current) else None


async def _discard_quietly(cover: str | None) -> None:
    try:
        await discard_unused_cover(get_database(), cover)
    except (RuntimeError, PyMongoError):
        pass  # ponytail: leaves an orphan file when the database is down; harmless


async def _page(request: Request, *, values: dict[str, Any], piece: ArticleRead | None = None, prompt: str = "", notice: str | None = None, **extra: Any):
    try:
        rooms = await get_rooms(get_database())
    except (RuntimeError, PyMongoError):
        rooms = []

    # The preview shows the generated cover for the chosen room until there is an image.
    slug = piece.slug if piece else "preview"
    room_covers = {room["slug"]: cover_url(room["slug"], slug) for room in rooms}
    own_cover = piece.cover_image if piece and piece.cover_image else ""

    return await render_form_page(
        request,
        TEMPLATE,
        "Edit your piece" if piece else "Write",
        values=values,
        piece=piece,
        rooms=rooms,
        room_covers=room_covers,
        own_cover=own_cover,
        has_uploaded_cover=bool(UPLOADED_COVER.match(own_cover)),
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
        # Only a pasted link goes back in the link field; an upload shows as the preview.
        "cover_url": "" if not piece.cover_image or UPLOADED_COVER.match(piece.cover_image) else piece.cover_image,
    }


def _login_redirect(request: Request) -> RedirectResponse:
    target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    return RedirectResponse(f"/login?next={quote(target, safe='')}", status_code=303)
