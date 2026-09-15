from __future__ import annotations

from typing import Any

from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_FORMAT_GUIDE, ARTICLE_FORMAT_REVIEW
from app.database.mongodb import get_database
from app.models.category import CATEGORY_COLLECTION


NAV_TOPIC_LIMIT = 8

# Every topic opens the same shaped panel. Sub-topics do not exist yet, so the
# second level is the article format, which the homepage rails already use.
NAV_FORMAT_LINKS: tuple[dict[str, str], ...] = (
    {"label": "Guides", "format": ARTICLE_FORMAT_GUIDE},
    {"label": "Reviews", "format": ARTICLE_FORMAT_REVIEW},
)

FALLBACK_TOPICS: tuple[dict[str, str], ...] = (
    {"name": "Business", "slug": "business"},
    {"name": "Tech", "slug": "tech"},
    {"name": "Food", "slug": "food"},
    {"name": "Travel", "slug": "travel"},
)


async def get_nav_context() -> dict[str, Any]:
    """Navigation shared by every public page.

    Built once here instead of per page, so header links behave the same
    everywhere rather than only on the homepage.
    """
    try:
        db = get_database()
        topics = await _get_topics(db)
    except (RuntimeError, PyMongoError):
        topics = [dict(topic) for topic in FALLBACK_TOPICS]

    if not topics:
        topics = [dict(topic) for topic in FALLBACK_TOPICS]

    nav_topics = [_build_topic(topic) for topic in topics]

    return {
        "nav_topics": nav_topics,
        "category_links": [
            {"name": topic["name"], "slug": topic["slug"], "url": topic["url"]}
            for topic in nav_topics
        ],
        "categories": [topic["name"] for topic in nav_topics],
    }


async def _get_topics(db: Any) -> list[dict[str, str]]:
    cursor = (
        db[CATEGORY_COLLECTION]
        .find({}, {"_id": 0, "name": 1, "slug": 1, "nav_order": 1})
        .sort([("nav_order", ASCENDING), ("name", ASCENDING)])
        .limit(NAV_TOPIC_LIMIT)
    )
    topics: list[dict[str, str]] = []

    async for category in cursor:
        name = str(category.get("name", "")).strip()
        slug = str(category.get("slug", "")).strip()
        if not name or not slug:
            continue

        topics.append({"name": name, "slug": slug})

    return topics


def _build_topic(topic: dict[str, str]) -> dict[str, Any]:
    slug = topic["slug"]
    topic_url = f"/articles?category={slug}"

    return {
        "name": topic["name"],
        "slug": slug,
        "url": topic_url,
        "links": [
            {"label": f"All {topic['name']}", "url": topic_url},
            *(
                {
                    "label": link["label"],
                    "url": f"{topic_url}&format={link['format']}",
                }
                for link in NAV_FORMAT_LINKS
            ),
            {"label": "Trending", "url": f"{topic_url}&sort=popular"},
        ],
    }
