"""Every public page search engines should know about, for /sitemap.xml.

Left out on purpose: drafts, hidden or archived items, answered Arcade views
(they are noindex), member profiles (too thin to index yet), and private pages.
"""

from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.question import QUESTION_COLLECTION
from app.models.quiz import QUIZ_COLLECTION
from app.services.nav_service import get_rooms
from app.services.question_service import site_today


# One sitemap file holds 50,000 URLs; split into an index before reaching it.
URL_LIMIT = 45_000
SECTION_PAGES = ("/", "/articles", "/categories", "/questions", "/experiences", "/play")


async def sitemap_entries(database: AsyncIOMotorDatabase | None = None) -> list[tuple[str, str | None]]:
    """(path, last-modified date or None), section pages first."""
    db = database if database is not None else get_database()
    entries: list[tuple[str, str | None]] = [(path, None) for path in SECTION_PAGES]
    entries += [(room["url"], None) for room in await get_rooms(db)]

    articles = db[ARTICLE_COLLECTION].find(
        {"status": ARTICLE_STATUS_PUBLISHED}, {"slug": 1, "updated_at": 1, "published_at": 1}
    ).sort([("published_at", DESCENDING)]).limit(URL_LIMIT)
    entries += [(f"/articles/{a['slug']}", _day(a.get("updated_at") or a.get("published_at"))) async for a in articles]

    questions = db[QUESTION_COLLECTION].find(
        {"status": "published", "publish_date": {"$lte": site_today()}}, {"slug": 1, "publish_date": 1}
    ).sort([("publish_date", DESCENDING)]).limit(URL_LIMIT)
    entries += [(f"/questions/{q['slug']}", q.get("publish_date")) async for q in questions]

    claims = db[QUIZ_COLLECTION].find({"status": "published"}, {"slug": 1, "updated_at": 1}).limit(URL_LIMIT)
    entries += [(f"/play/{c['slug']}", _day(c.get("updated_at"))) async for c in claims]

    return entries[:URL_LIMIT]


def _day(value: Any) -> str | None:
    return value.date().isoformat() if isinstance(value, datetime) else None
