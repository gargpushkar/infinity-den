from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.config.constants import (
    ARTICLE_FORMAT_GUIDE,
    ARTICLE_FORMAT_REVIEW,
    ARTICLE_STATUS_PUBLISHED,
)
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.schemas.article import ArticleRead
from app.services.article_page_service import article_to_card_context


FEATURED_ARTICLE_LIMIT = 3
RAIL_ARTICLE_LIMIT = 3
CATEGORY_LINK_LIMIT = 8

PUBLISHED = {"status": ARTICLE_STATUS_PUBLISHED}

RECENT_SORT: list[tuple[str, int]] = [
    ("published_at", DESCENDING),
    ("created_at", DESCENDING),
]

# Each rail is one row of three cards on the homepage.
RAIL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "trending",
        "title": "Trending",
        "subtitle": "What readers are opening most right now.",
        "filter": PUBLISHED,
        "sort": [("views", DESCENDING), ("published_at", DESCENDING)],
        "url": "/articles?sort=popular",
    },
    {
        "key": "editors-picks",
        "title": "Editor's Picks",
        "subtitle": "Hand-chosen by the editorial desk.",
        "filter": {**PUBLISHED, "is_editors_pick": True},
        "sort": RECENT_SORT,
        "url": "/articles",
    },
    {
        "key": "latest",
        "title": "Latest",
        "subtitle": "Fresh off the publishing queue.",
        "filter": PUBLISHED,
        "sort": RECENT_SORT,
        "url": "/articles",
    },
    {
        "key": "guides",
        "title": "Guides",
        "subtitle": "Step-by-step explainers worth bookmarking.",
        "filter": {
            **PUBLISHED,
            "article_format": ARTICLE_FORMAT_GUIDE,
        },
        "sort": RECENT_SORT,
        "url": f"/articles?format={ARTICLE_FORMAT_GUIDE}",
    },
    {
        "key": "reviews",
        "title": "Reviews",
        "subtitle": "Tested, rated, and written up honestly.",
        "filter": {
            **PUBLISHED,
            "article_format": ARTICLE_FORMAT_REVIEW,
        },
        "sort": RECENT_SORT,
        "url": f"/articles?format={ARTICLE_FORMAT_REVIEW}",
    },
)


async def get_homepage_context() -> dict[str, Any]:
    try:
        db = get_database()
        category_options = await _get_category_links(db)
        category_lookup = {
            category["slug"]: category["name"] for category in category_options
        }
        featured_articles = await _get_featured_articles(db, category_lookup)
        rails = await _get_rails(db, category_lookup)
        latest_articles = _rail_articles(rails, "latest")

        if not featured_articles:
            featured_articles = latest_articles[:FEATURED_ARTICLE_LIMIT]

        if not category_options and not latest_articles:
            return _fallback_homepage_context()

        article_count = await db[ARTICLE_COLLECTION].count_documents(PUBLISHED)
        featured_count = await db[ARTICLE_COLLECTION].count_documents(
            {**PUBLISHED, "is_featured": True}
        )

        return {
            "hero_metrics": _hero_metrics(
                article_count=article_count,
                category_count=len(category_options),
                featured_count=featured_count,
            ),
            "top_articles": featured_articles,
            "featured_articles": featured_articles,
            "article_rails": rails,
            "latest_articles": latest_articles,
            "categories": [category["name"] for category in category_options],
            "category_links": category_options,
        }
    except (RuntimeError, PyMongoError):
        return _fallback_homepage_context()


async def _get_rails(
    db: Any,
    category_lookup: dict[str, str],
) -> list[dict[str, Any]]:
    """Build the homepage rails, dropping any that have nothing to show.

    An empty rail is worse than a missing one: it reads as broken rather than
    as a section you have not filled yet.
    """
    rails: list[dict[str, Any]] = []

    for definition in RAIL_DEFINITIONS:
        articles = await _get_article_cards(
            db,
            definition["filter"],
            category_lookup,
            definition["sort"],
            RAIL_ARTICLE_LIMIT,
        )
        if not articles:
            continue

        rails.append(
            {
                "key": definition["key"],
                "title": definition["title"],
                "subtitle": definition["subtitle"],
                "url": definition["url"],
                "articles": articles,
            }
        )

    return rails


def _rail_articles(rails: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    for rail in rails:
        if rail["key"] == key:
            return rail["articles"]

    return []


async def _get_category_links(db: Any) -> list[dict[str, Any]]:
    cursor = (
        db[CATEGORY_COLLECTION]
        .find({}, {"_id": 0, "name": 1, "slug": 1, "nav_order": 1})
        .sort([("nav_order", ASCENDING), ("name", ASCENDING)])
        .limit(CATEGORY_LINK_LIMIT)
    )
    categories: list[dict[str, Any]] = []

    async for category in cursor:
        slug = str(category.get("slug", "")).strip()
        name = str(category.get("name", "")).strip()
        if not slug or not name:
            continue

        categories.append(
            {
                "name": name,
                "slug": slug,
                "url": f"/articles?category={slug}",
            }
        )

    return categories


async def _get_featured_articles(
    db: Any,
    category_lookup: dict[str, str],
) -> list[dict[str, Any]]:
    return await _get_article_cards(
        db,
        {**PUBLISHED, "is_featured": True},
        category_lookup,
        [
            ("published_at", DESCENDING),
            ("updated_at", DESCENDING),
            ("created_at", DESCENDING),
        ],
        FEATURED_ARTICLE_LIMIT,
    )


async def _get_article_cards(
    db: Any,
    article_filter: dict[str, Any],
    category_lookup: dict[str, str],
    sort: list[tuple[str, int]],
    limit: int,
) -> list[dict[str, Any]]:
    cursor = db[ARTICLE_COLLECTION].find(article_filter).sort(sort).limit(limit)

    return [
        article_to_card_context(
            ArticleRead.model_validate(article),
            category_lookup,
        )
        async for article in cursor
    ]


def _hero_metrics(
    *,
    article_count: int,
    category_count: int,
    featured_count: int,
) -> list[dict[str, str]]:
    return [
        {"value": str(article_count), "label": "Stories published"},
        {"value": str(category_count), "label": "Sections"},
        {"value": str(featured_count), "label": "Featured now"},
    ]


def _fallback_homepage_context() -> dict[str, Any]:
    """Rendered when MongoDB is unreachable, so the homepage still stands up."""
    category_links = [
        {"name": "Business", "slug": "business", "url": "/articles?category=business"},
        {"name": "Tech", "slug": "tech", "url": "/articles?category=tech"},
        {"name": "Food", "slug": "food", "url": "/articles?category=food"},
        {"name": "Travel", "slug": "travel", "url": "/articles?category=travel"},
    ]

    return {
        "hero_metrics": _hero_metrics(
            article_count=0,
            category_count=len(category_links),
            featured_count=0,
        ),
        "top_articles": [],
        "featured_articles": [],
        "article_rails": [],
        "latest_articles": [],
        "categories": [category["name"] for category in category_links],
        "category_links": category_links,
    }
