from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_FORMAT_LABELS, ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.schemas.article import ArticleQueryParams
from app.schemas.category import CategoryRead
from app.services.article_page_service import article_to_card_context, room_url
from app.services.article_service import ArticleService
from app.services.category_service import CategoryService
from app.utils.covers import resolve_cover


CATEGORY_DETAIL_PER_PAGE = 6



async def get_category_listing_context() -> dict[str, Any]:
    """Every room, in navigation order, with how many published pieces it holds."""
    try:
        rooms = await _rooms_with_counts(get_database())
    except (RuntimeError, PyMongoError):
        return {"category_cards": [], "category_count": 0, "total_published_articles": 0, "is_database_available": False}
    return {
        "category_cards": [_category_to_card(room, room["article_count"]) for room in rooms],
        "category_count": len(rooms),
        "total_published_articles": sum(room["article_count"] for room in rooms),
        "is_database_available": True,
    }


async def _rooms_with_counts(db: Any) -> list[dict[str, Any]]:
    pipeline = [
        {
            "$lookup": {
                "from": ARTICLE_COLLECTION,
                "let": {"category_slug": "$slug"},
                "pipeline": [
                    {"$match": {"$expr": {"$and": [
                        {"$eq": ["$category_id", "$$category_slug"]},
                        {"$eq": ["$status", ARTICLE_STATUS_PUBLISHED]},
                    ]}}},
                    {"$count": "total"},
                ],
                "as": "article_stats",
            }
        },
        {"$addFields": {"article_count": {"$ifNull": [{"$arrayElemAt": ["$article_stats.total", 0]}, 0]}}},
        {"$sort": {"nav_order": 1, "name": 1}},
    ]
    return await db[CATEGORY_COLLECTION].aggregate(pipeline).to_list(length=None)


async def get_category_detail_context(
    *,
    category_slug: str,
    page: int,
    article_format: str | None = None,
) -> dict[str, Any] | None:
    try:
        db = get_database()
        category_service = CategoryService(database=db)
        category = await category_service.get_category_by_slug(category_slug)
        if category is None:
            return None

        # Unknown formats fall back to "all" rather than an empty page.
        format_filter = article_format if article_format in ARTICLE_FORMAT_LABELS else None
        article_query = ArticleQueryParams(
            page=page,
            per_page=CATEGORY_DETAIL_PER_PAGE,
            status=ARTICLE_STATUS_PUBLISHED,
            category_id=category.slug,
            article_format=format_filter,
            sort_by="published_at",
            sort_direction="desc",
        )
        article_list = await ArticleService(database=db).list_articles(article_query)
        category_lookup = {category.slug: category.name}
        articles = [
            article_to_card_context(article, category_lookup)
            for article in article_list.items
        ]

        return {
            "category": _category_to_detail(category, article_list.total),
            "articles": articles,
            "article_count": article_list.total,
            "pagination": {
                "current_page": article_list.page,
                "total_pages": article_list.total_pages,
                "total_items": article_list.total,
                "per_page": article_list.per_page,
                "url_template": _room_page_url(category.slug, format_filter, page="{page}"),
                "aria_label": f"{category.name} article pages",
            },
            "format_filters": _format_filters(category.slug, format_filter),
            "categories": await _get_category_names(db),
            "is_database_available": True,
        }
    except (RuntimeError, PyMongoError):
        return None


async def _get_category_names(db: Any) -> list[str]:
    names: list[str] = []
    cursor = db.categories.find({}, {"_id": 0, "name": 1}).sort("name", 1)

    async for category in cursor:
        name = str(category.get("name", "")).strip()
        if name:
            names.append(name)

    return names


def _category_to_card(
    category: CategoryRead | dict[str, Any],
    article_count: int,
) -> dict[str, Any]:
    category_data = _category_read_context(category)

    return {
        "name": category_data["name"],
        "slug": category_data["slug"],
        "subtitle": category_data["subtitle"],
        "description": category_data["description"]
        or "A collection of ideas, stories, and perspectives from this room.",
        "image": resolve_cover(category_data["image"], category_data["slug"], category_data["slug"]),
        "image_alt": f"{category_data['name']} category",
        "article_count": article_count,
        "article_count_label": _format_article_count(article_count),
        "category_url": room_url(category_data["slug"]),
    }


def _category_to_detail(
    category: CategoryRead,
    article_count: int,
) -> dict[str, Any]:
    description = (
        category.description
        or "A collection of ideas, stories, and perspectives from this room."
    )

    return {
        "name": category.name,
        "subtitle": category.subtitle or "",
        "slug": category.slug,
        "description": description,
        "image": resolve_cover(category.image, category.slug, category.slug),
        "image_alt": f"{category.name} category",
        "article_count": article_count,
        "article_count_label": _format_article_count(article_count),
        "category_url": room_url(category.slug),
        "seo_title": (
            f"{category.name}: {category.subtitle}" if category.subtitle else category.name
        ),
        "seo_description": _truncate_meta_description(description),
    }


def _room_page_url(slug: str, article_format: str | None, *, page: str | None = None) -> str:
    params = {"format": article_format} if article_format else {}
    if page:
        params["page"] = "__page__"
    query = urlencode(params).replace("__page__", page or "")

    return f"{room_url(slug)}?{query}" if query else room_url(slug)


def _format_filters(slug: str, active_format: str | None) -> list[dict[str, Any]]:
    options = [(None, "All"), *ARTICLE_FORMAT_LABELS.items()]

    return [
        {
            "label": label,
            "url": _room_page_url(slug, value),
            "is_active": value == active_format,
        }
        for value, label in options
    ]


def _format_article_count(article_count: int) -> str:
    if article_count == 1:
        return "1 article"

    return f"{article_count} articles"


def _category_read_context(category: CategoryRead | dict[str, Any]) -> dict[str, Any]:
    if isinstance(category, CategoryRead):
        return {
            "name": category.name,
            "subtitle": category.subtitle or "",
            "slug": category.slug,
            "description": category.description,
            "image": category.image,
        }

    return {
        "name": str(category.get("name", "")).strip(),
        "subtitle": str(category.get("subtitle") or "").strip(),
        "slug": str(category.get("slug", "")).strip(),
        "description": category.get("description"),
        "image": category.get("image"),
    }


def _truncate_meta_description(value: str) -> str:
    clean_value = " ".join(str(value or "").split())
    if len(clean_value) <= 160:
        return clean_value

    return f"{clean_value[:157].rstrip()}..."


