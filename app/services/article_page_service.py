from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.schemas.article import ArticleQueryParams, ArticleRead
from app.services.article_service import ArticleService


ARTICLE_LISTING_PER_PAGE = 6

SORT_OPTIONS: tuple[dict[str, str], ...] = (
    {
        "label": "Newest",
        "value": "newest",
        "sort_by": "published_at",
        "sort_direction": "desc",
    },
    {
        "label": "Oldest",
        "value": "oldest",
        "sort_by": "published_at",
        "sort_direction": "asc",
    },
    {
        "label": "Most viewed",
        "value": "popular",
        "sort_by": "views",
        "sort_direction": "desc",
    },
    {
        "label": "Title A-Z",
        "value": "title",
        "sort_by": "title",
        "sort_direction": "asc",
    },
)


async def get_article_listing_context(
    *,
    page: int,
    category: str | None,
    tag: str | None,
    sort: str,
) -> dict[str, Any]:
    try:
        db = get_database()
        category_options = await _get_category_options(db)
        tag_options = await _get_tag_options(db)
        sort_option = _resolve_sort_option(sort)
        category_filter = _clean_optional_slug(category)
        tag_filter = _clean_optional_tag(tag)

        query = ArticleQueryParams(
            page=page,
            per_page=ARTICLE_LISTING_PER_PAGE,
            status="published",
            category_id=category_filter,
            tag=tag_filter,
            sort_by=sort_option["sort_by"],
            sort_direction=sort_option["sort_direction"],
        )
        article_list = await ArticleService(database=db).list_articles(query)
        category_lookup = {item["slug"]: item["name"] for item in category_options}
        articles = [
            _article_to_card(article, category_lookup)
            for article in article_list.items
        ]

        return {
            "articles": articles,
            "article_count": article_list.total,
            "pagination": {
                "current_page": article_list.page,
                "total_pages": article_list.total_pages,
                "total_items": article_list.total,
                "per_page": article_list.per_page,
                "url_template": _pagination_url_template(
                    category_filter,
                    tag_filter,
                    sort_option["value"],
                ),
                "aria_label": "Article pages",
            },
            "category_filters": _mark_active_filter(category_options, category_filter),
            "tag_filters": _mark_active_filter(tag_options, tag_filter),
            "sort_options": _mark_active_filter(list(SORT_OPTIONS), sort_option["value"]),
            "active_category": category_lookup.get(category_filter or ""),
            "active_tag": tag_filter,
            "active_sort": sort_option["label"],
            "categories": [item["name"] for item in category_options],
            "is_database_available": True,
        }
    except (RuntimeError, PyMongoError):
        return _empty_listing_context()


async def _get_category_options(db: Any) -> list[dict[str, Any]]:
    categories = []
    cursor = db.categories.find({}, {"_id": 0}).sort("name", ASCENDING)

    async for category in cursor:
        slug = str(category.get("slug", "")).strip()
        name = str(category.get("name", "")).strip()
        if not slug or not name:
            continue

        total = await db[ARTICLE_COLLECTION].count_documents(
            {"category_id": slug, "status": "published"}
        )
        categories.append(
            {
                "name": name,
                "slug": slug,
                "value": slug,
                "url": f"/articles?{urlencode({'category': slug})}",
                "total": total,
            }
        )

    return categories


async def _get_tag_options(db: Any) -> list[dict[str, str]]:
    tags = []
    cursor = db.tags.find({}, {"_id": 0}).sort("name", ASCENDING)

    async for tag in cursor:
        slug = str(tag.get("slug", "")).strip()
        name = str(tag.get("name", "")).strip()
        if not slug or not name:
            continue

        tags.append({"name": name, "slug": slug, "value": name})

    return tags


def _article_to_card(
    article: ArticleRead,
    category_lookup: dict[str, str],
) -> dict[str, Any]:
    published_at = _format_date(article.published_at)
    read_time = max(1, round(len(article.content.split()) / 220))

    return {
        "title": article.title,
        "slug": article.slug,
        "url": f"/articles/{article.slug}",
        "excerpt": article.excerpt,
        "category": category_lookup.get(article.category_id or "", "Article"),
        "read_time": f"{read_time} min read",
        "cover_image": article.cover_image or "/static/images/articles/editorial-default.svg",
        "image_alt": article.title,
        "author": article.author,
        "published_label": published_at,
        "views": article.views,
        "tags": article.tags,
    }


def _resolve_sort_option(sort: str) -> dict[str, Any]:
    clean_sort = str(sort or "").strip().lower()

    for option in SORT_OPTIONS:
        if option["value"] == clean_sort:
            return {
                "label": option["label"],
                "value": option["value"],
                "sort_by": option["sort_by"],
                "sort_direction": option["sort_direction"],
            }

    default_option = SORT_OPTIONS[0]
    return {
        "label": default_option["label"],
        "value": default_option["value"],
        "sort_by": default_option["sort_by"],
        "sort_direction": default_option["sort_direction"],
    }


def _mark_active_filter(
    options: list[dict[str, Any]],
    active_value: str | None,
) -> list[dict[str, Any]]:
    return [
        {
            **option,
            "is_active": option.get("value") == active_value,
        }
        for option in options
    ]


def _pagination_url_template(
    category: str | None,
    tag: str | None,
    sort: str,
) -> str:
    params = {"page": "__page__", "sort": sort}
    if category:
        params["category"] = category
    if tag:
        params["tag"] = tag

    return f"/articles?{urlencode(params)}".replace("__page__", "{page}")


def _clean_optional_slug(value: str | None) -> str | None:
    if value is None:
        return None

    clean_value = value.strip().lower()
    return clean_value or None


def _clean_optional_tag(value: str | None) -> str | None:
    if value is None:
        return None

    clean_value = value.strip()
    return clean_value or None


def _format_date(value: datetime | None) -> str:
    if value is None:
        return "Draft"

    return f"{value:%b} {value.day}, {value:%Y}"


def _empty_listing_context() -> dict[str, Any]:
    return {
        "articles": [],
        "article_count": 0,
        "pagination": {
            "current_page": 1,
            "total_pages": 0,
            "total_items": 0,
            "per_page": ARTICLE_LISTING_PER_PAGE,
            "url_template": "/articles?page={page}",
            "aria_label": "Article pages",
        },
        "category_filters": [],
        "tag_filters": [],
        "sort_options": _mark_active_filter(list(SORT_OPTIONS), "newest"),
        "active_category": None,
        "active_tag": None,
        "active_sort": "Newest",
        "categories": [],
        "is_database_available": False,
    }
