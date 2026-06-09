from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.schemas.category import CategoryQueryParams, CategoryRead
from app.services.category_service import CategoryService


CATEGORY_LISTING_PER_PAGE = 9


async def get_category_listing_context(*, page: int) -> dict[str, Any]:
    try:
        db = get_database()
        query = CategoryQueryParams(
            page=page,
            per_page=CATEGORY_LISTING_PER_PAGE,
            sort_by="name",
            sort_direction="asc",
        )
        category_list = await CategoryService(database=db).list_categories(query)
        article_counts = await _get_published_article_counts(db)
        categories = [
            _category_to_card(category, article_counts.get(category.slug, 0))
            for category in category_list.items
        ]

        return {
            "categories": [category.name for category in category_list.items],
            "category_cards": categories,
            "category_count": category_list.total,
            "total_published_articles": sum(article_counts.values()),
            "pagination": {
                "current_page": category_list.page,
                "total_pages": category_list.total_pages,
                "total_items": category_list.total,
                "per_page": category_list.per_page,
                "url_template": "/categories?page={page}",
                "aria_label": "Category pages",
            },
            "is_database_available": True,
        }
    except (RuntimeError, PyMongoError):
        return _empty_category_listing_context()


async def _get_published_article_counts(db: Any) -> dict[str, int]:
    article_counts: dict[str, int] = {}
    pipeline = [
        {"$match": {"status": ARTICLE_STATUS_PUBLISHED, "category_id": {"$ne": None}}},
        {"$group": {"_id": "$category_id", "total": {"$sum": 1}}},
    ]

    async for item in db[ARTICLE_COLLECTION].aggregate(pipeline):
        category_slug = str(item.get("_id", "")).strip()
        if category_slug:
            article_counts[category_slug] = int(item.get("total", 0))

    return article_counts


def _category_to_card(
    category: CategoryRead,
    article_count: int,
) -> dict[str, Any]:
    return {
        "name": category.name,
        "slug": category.slug,
        "description": category.description
        or "A focused collection of articles from this editorial lane.",
        "image": category.image or "/static/images/articles/editorial-default.svg",
        "image_alt": f"{category.name} category",
        "article_count": article_count,
        "article_count_label": _format_article_count(article_count),
        "articles_url": f"/articles?{urlencode({'category': category.slug})}",
    }


def _format_article_count(article_count: int) -> str:
    if article_count == 1:
        return "1 article"

    return f"{article_count} articles"


def _empty_category_listing_context() -> dict[str, Any]:
    return {
        "categories": [],
        "category_cards": [],
        "category_count": 0,
        "total_published_articles": 0,
        "pagination": {
            "current_page": 1,
            "total_pages": 0,
            "total_items": 0,
            "per_page": CATEGORY_LISTING_PER_PAGE,
            "url_template": "/categories?page={page}",
            "aria_label": "Category pages",
        },
        "is_database_available": False,
    }
