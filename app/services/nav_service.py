from __future__ import annotations

from typing import Any

from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.config.constants import LAUNCH_ROOMS
from app.database.mongodb import get_database
from app.models.category import CATEGORY_COLLECTION
from app.services.article_page_service import room_url


NAV_ROOM_LIMIT = 12


async def get_nav_context() -> dict[str, Any]:
    """Navigation shared by every public page.

    Built once here instead of per page, so header links behave the same
    everywhere rather than only on the homepage.
    """
    try:
        rooms = await get_rooms(get_database())
    except (RuntimeError, PyMongoError):
        rooms = []

    rooms = rooms or fallback_rooms()

    return {
        "nav_rooms": rooms,
        "category_links": rooms,
        "categories": [room["name"] for room in rooms],
    }


async def get_rooms(db: Any) -> list[dict[str, Any]]:
    """Rooms in navigation order, each with its display name and subtitle."""
    cursor = (
        db[CATEGORY_COLLECTION]
        .find({}, {"_id": 0, "name": 1, "subtitle": 1, "slug": 1, "nav_order": 1})
        .sort([("nav_order", ASCENDING), ("name", ASCENDING)])
        .limit(NAV_ROOM_LIMIT)
    )
    rooms: list[dict[str, Any]] = []

    async for category in cursor:
        name = str(category.get("name", "")).strip()
        slug = str(category.get("slug", "")).strip()
        if not name or not slug:
            continue

        rooms.append(_room(name, slug, category.get("subtitle")))

    return rooms


def fallback_rooms() -> list[dict[str, Any]]:
    """The launch rooms, used when the database is unreachable or empty."""
    return [
        _room(str(room["name"]), str(room["slug"]), str(room["subtitle"]))
        for room in LAUNCH_ROOMS
    ]


def _room(name: str, slug: str, subtitle: Any) -> dict[str, Any]:
    return {
        "name": name,
        "subtitle": str(subtitle or "").strip(),
        "slug": slug,
        "url": room_url(slug),
    }
