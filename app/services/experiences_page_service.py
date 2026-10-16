from typing import Any
from urllib.parse import urlencode

from pymongo.errors import PyMongoError

from app.config.constants import (
    ARTICLE_FORMAT_EXPERIENCE,
    ARTICLE_STATUS_PUBLISHED,
    HUMAN_LIBRARY_PROMPTS,
)
from app.database.mongodb import get_database
from app.schemas.article import ArticleQueryParams
from app.services.article_page_service import article_to_card_context
from app.services.article_service import ArticleService
from app.services.nav_service import fallback_rooms, get_rooms


EXPERIENCES_PER_PAGE = 9


async def get_experiences_context(*, page: int, room: str | None) -> dict[str, Any]:
    """The Human Library: every published personal experience, by room."""
    prompts = [
        {"text": text, "url": f"/write?{urlencode({'format': ARTICLE_FORMAT_EXPERIENCE, 'prompt': index})}"}
        for index, text in enumerate(HUMAN_LIBRARY_PROMPTS)
    ]
    try:
        db = get_database()
        rooms = await get_rooms(db)
        active_room = room if any(r["slug"] == room for r in rooms) else None
        listing = await ArticleService(database=db).list_articles(
            ArticleQueryParams(
                page=page,
                per_page=EXPERIENCES_PER_PAGE,
                status=ARTICLE_STATUS_PUBLISHED,
                article_format=ARTICLE_FORMAT_EXPERIENCE,
                category_id=active_room,
            )
        )
    except (RuntimeError, PyMongoError):
        return {"prompts": prompts, "room_filters": [], "pieces": [], "pagination": {}, "is_database_available": False}

    room_lookup = {r["slug"]: r["name"] for r in rooms}
    return {
        "prompts": prompts,
        "room_filters": [
            {"label": "All rooms", "url": "/experiences", "is_active": active_room is None},
            *(
                {"label": r["name"], "url": f"/experiences?{urlencode({'room': r['slug']})}", "is_active": r["slug"] == active_room}
                for r in rooms
            ),
        ],
        "pieces": [article_to_card_context(piece, room_lookup) for piece in listing.items],
        "pagination": {
            "current_page": listing.page,
            "total_pages": listing.total_pages,
            "total_items": listing.total,
            "per_page": listing.per_page,
            "url_template": "/experiences?" + (f"room={active_room}&" if active_room else "") + "page={page}",
            "aria_label": "Human Library pages",
        },
        "is_database_available": True,
    }
