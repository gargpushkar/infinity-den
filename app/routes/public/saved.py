from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pymongo.errors import PyMongoError

from app.database.mongodb import get_database
from app.routes.public.form_pages import render_form_page
from app.services.article_page_service import article_to_card_context
from app.services.bookmark_service import BookmarkService
from app.services.member_session import get_current_member
from app.services.nav_service import get_rooms


router = APIRouter()


@router.get("/saved")
async def saved_page(request: Request):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse("/login?next=/saved", status_code=303)

    try:
        db = get_database()
        room_names = {room["slug"]: room["name"] for room in await get_rooms(db)}
        pieces = [article_to_card_context(article, room_names) for article in await BookmarkService(database=db).saved_articles(member)]
        is_unavailable = False
    except (RuntimeError, PyMongoError):
        pieces, is_unavailable = [], True

    return await render_form_page(
        request,
        "pages/saved.html",
        "Saved",
        values={},
        pieces=pieces,
        is_unavailable=is_unavailable,
    )
