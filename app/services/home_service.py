from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.schemas.article import ArticleRead
from app.services.article_page_service import article_to_card_context


FEATURED_ARTICLE_LIMIT = 3
LATEST_ARTICLE_LIMIT = 5
CATEGORY_LINK_LIMIT = 5


async def get_homepage_context() -> dict[str, Any]:
    try:
        db = get_database()
        category_options = await _get_category_links(db)
        category_lookup = {
            category["slug"]: category["name"] for category in category_options
        }
        featured_articles = await _get_featured_articles(db, category_lookup)
        latest_articles = await _get_latest_articles(db, category_lookup)

        if not featured_articles:
            featured_articles = latest_articles[:FEATURED_ARTICLE_LIMIT]

        article_count = await db[ARTICLE_COLLECTION].count_documents(
            {"status": ARTICLE_STATUS_PUBLISHED}
        )
        featured_count = await db[ARTICLE_COLLECTION].count_documents(
            {
                "status": ARTICLE_STATUS_PUBLISHED,
                "is_featured": True,
            }
        )

        if not category_options and not latest_articles:
            return _fallback_homepage_context()

        return {
            "hero_metrics": _hero_metrics(
                article_count=article_count,
                category_count=len(category_options),
                featured_count=featured_count,
            ),
            "top_articles": featured_articles,
            "featured_articles": featured_articles,
            "latest_articles": latest_articles,
            "categories": [category["name"] for category in category_options],
            "category_links": category_options,
        }
    except (RuntimeError, PyMongoError):
        return _fallback_homepage_context()


async def _get_category_links(db: Any) -> list[dict[str, Any]]:
    cursor = (
        db[CATEGORY_COLLECTION]
        .find({}, {"_id": 0, "name": 1, "slug": 1})
        .sort("name", ASCENDING)
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
        {
            "status": ARTICLE_STATUS_PUBLISHED,
            "is_featured": True,
        },
        category_lookup,
        [
            ("published_at", DESCENDING),
            ("updated_at", DESCENDING),
            ("created_at", DESCENDING),
        ],
        FEATURED_ARTICLE_LIMIT,
    )


async def _get_latest_articles(
    db: Any,
    category_lookup: dict[str, str],
) -> list[dict[str, Any]]:
    return await _get_article_cards(
        db,
        {"status": ARTICLE_STATUS_PUBLISHED},
        category_lookup,
        [
            ("published_at", DESCENDING),
            ("created_at", DESCENDING),
        ],
        LATEST_ARTICLE_LIMIT,
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
        {"value": str(article_count), "label": "Published articles"},
        {"value": str(category_count), "label": "Topic hubs"},
        {"value": str(featured_count), "label": "Featured stories"},
    ]


def _fallback_homepage_context() -> dict[str, Any]:
    category_links = [
        {
            "name": "Content Strategy",
            "slug": "content-strategy",
            "url": "/articles?category=content-strategy",
        },
        {
            "name": "Search Growth",
            "slug": "search-growth",
            "url": "/articles?category=search-growth",
        },
        {
            "name": "Editorial Ops",
            "slug": "editorial-ops",
            "url": "/articles?category=editorial-ops",
        },
        {
            "name": "Audience Building",
            "slug": "audience-building",
            "url": "/articles?category=audience-building",
        },
        {
            "name": "Newsletter",
            "slug": "newsletter",
            "url": "/search?q=newsletter",
        },
    ]
    featured_articles = [
        {
            "title": "Editorial systems that scale with your audience",
            "url": "/articles?category=editorial-ops",
            "excerpt": "A practical look at building a publishing rhythm, review process, and SEO workflow without slowing the team down.",
            "category": "Editorial",
            "read_time": "8 min read",
            "cover_image": "/static/images/articles/editorial-default.svg",
            "image_alt": "Abstract editorial article layout",
        },
        {
            "title": "How to turn category pages into growth assets",
            "url": "/categories",
            "excerpt": "Use focused topic hubs to make discovery easier for readers and search engines.",
            "category": "SEO",
            "read_time": "6 min read",
            "cover_image": "/static/images/articles/search-traffic.svg",
            "image_alt": "Search growth dashboard illustration",
        },
        {
            "title": "A cleaner intake process for guest contributors",
            "url": "/#writeForUs",
            "excerpt": "Collect ideas, triage submissions, and protect the quality bar from the first message.",
            "category": "Community",
            "read_time": "5 min read",
            "cover_image": "/static/images/articles/contributors.svg",
            "image_alt": "Contributor collaboration illustration",
        },
    ]
    latest_articles = [
        {
            "title": "A weekly editorial review that keeps teams aligned",
            "url": "/articles?category=editorial-ops",
            "excerpt": "Use a short review ritual to spot stale drafts, unblock approvals, and keep the publishing calendar honest.",
            "category": "Editorial",
            "cover_image": "/static/images/articles/editorial-default.svg",
            "image_alt": "Editorial planning board with article cards",
            "read_time": "7 min read",
        },
        {
            "title": "What to measure before refreshing old content",
            "url": "/search?q=content+refresh",
            "excerpt": "Prioritize updates with search intent, decay signals, and conversion context instead of chasing every aging post.",
            "category": "Growth",
            "cover_image": "/static/images/articles/search-traffic.svg",
            "image_alt": "Search analytics charts for content refresh decisions",
            "read_time": "6 min read",
        },
        {
            "title": "Turn contributor pitches into a reliable intake queue",
            "url": "/#writeForUs",
            "excerpt": "Separate promising ideas from noisy submissions with clear prompts, topic lanes, and review states.",
            "category": "Community",
            "cover_image": "/static/images/articles/contributors.svg",
            "image_alt": "Contributors reviewing article ideas together",
            "read_time": "5 min read",
        },
    ]

    return {
        "hero_metrics": _hero_metrics(
            article_count=len(latest_articles),
            category_count=len(category_links),
            featured_count=len(featured_articles),
        ),
        "top_articles": featured_articles,
        "featured_articles": featured_articles,
        "latest_articles": latest_articles,
        "categories": [category["name"] for category in category_links],
        "category_links": category_links,
    }
