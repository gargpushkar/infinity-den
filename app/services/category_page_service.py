from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.schemas.article import ArticleQueryParams
from app.schemas.category import CategoryQueryParams, CategoryRead
from app.services.article_page_service import article_to_card_context
from app.services.article_service import ArticleService
from app.services.category_service import CategoryService


CATEGORY_LISTING_PER_PAGE = 9
CATEGORY_DETAIL_PER_PAGE = 6


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


async def get_category_detail_context(
    *,
    category_slug: str,
    page: int,
) -> dict[str, Any] | None:
    try:
        db = get_database()
        category_service = CategoryService(database=db)
        category = await category_service.get_category_by_slug(category_slug)
        if category is None:
            return None

        article_query = ArticleQueryParams(
            page=page,
            per_page=CATEGORY_DETAIL_PER_PAGE,
            status=ARTICLE_STATUS_PUBLISHED,
            category_id=category.slug,
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
                "url_template": f"/categories/{category.slug}?page={{page}}",
                "aria_label": f"{category.name} article pages",
            },
            "categories": await _get_category_names(db),
            "is_database_available": True,
        }
    except (RuntimeError, PyMongoError):
        return None


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


async def _get_category_names(db: Any) -> list[str]:
    names: list[str] = []
    cursor = db.categories.find({}, {"_id": 0, "name": 1}).sort("name", 1)

    async for category in cursor:
        name = str(category.get("name", "")).strip()
        if name:
            names.append(name)

    return names


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
        "category_url": f"/categories/{category.slug}",
        "articles_url": f"/articles?{urlencode({'category': category.slug})}",
    }


def _category_to_detail(
    category: CategoryRead,
    article_count: int,
) -> dict[str, Any]:
    description = (
        category.description
        or "A focused collection of articles from this editorial lane."
    )

    return {
        "name": category.name,
        "slug": category.slug,
        "description": description,
        "image": category.image or "/static/images/articles/editorial-default.svg",
        "image_alt": f"{category.name} category",
        "article_count": article_count,
        "article_count_label": _format_article_count(article_count),
        "category_url": f"/categories/{category.slug}",
        "articles_url": f"/articles?{urlencode({'category': category.slug})}",
        "seo_title": f"{category.name} Articles",
        "seo_description": _truncate_meta_description(
            f"{description} Browse the latest {category.name} articles and guides."
        ),
    }


def _format_article_count(article_count: int) -> str:
    if article_count == 1:
        return "1 article"

    return f"{article_count} articles"


def _truncate_meta_description(value: str) -> str:
    clean_value = " ".join(str(value or "").split())
    if len(clean_value) <= 160:
        return clean_value

    return f"{clean_value[:157].rstrip()}..."


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
