from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.schemas.article import ArticleQueryParams, ArticleRead
from app.services.article_service import ArticleService
from app.utils.reading_time import calculate_reading_time


ARTICLE_LISTING_PER_PAGE = 6
RELATED_ARTICLE_LIMIT = 3

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


async def get_article_detail_context(article_slug: str) -> dict[str, Any] | None:
    try:
        db = get_database()
        category_options = await _get_category_options(db)
        category_lookup = {item["slug"]: item["name"] for item in category_options}
        article = await ArticleService(database=db).get_article_detail(article_slug)

        if article is None or article.status != "published":
            return None

        article_context = _article_to_detail(article, category_lookup)
        related_articles = await _get_related_articles(db, article, category_lookup)

        return {
            "article": article_context,
            "related_articles": related_articles,
            "categories": [item["name"] for item in category_options],
            "is_database_available": True,
        }
    except (RuntimeError, PyMongoError):
        return None


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


async def _get_related_articles(
    db: Any,
    article: ArticleRead,
    category_lookup: dict[str, str],
) -> list[dict[str, Any]]:
    related_filters: list[dict[str, Any]] = []
    if article.category_id:
        related_filters.append({"category_id": article.category_id})
    if article.tags:
        related_filters.append({"tags": {"$in": article.tags}})

    selected_slugs = {article.slug}
    related_articles: list[dict[str, Any]] = []

    if related_filters:
        primary_filter: dict[str, Any] = {
            "status": ARTICLE_STATUS_PUBLISHED,
            "slug": {"$ne": article.slug},
            "$or": related_filters,
        }
        related_articles = await _fetch_related_article_cards(
            db,
            primary_filter,
            category_lookup,
            RELATED_ARTICLE_LIMIT,
        )
        selected_slugs.update(item["slug"] for item in related_articles)

    if len(related_articles) < RELATED_ARTICLE_LIMIT:
        fallback_filter = {
            "status": ARTICLE_STATUS_PUBLISHED,
            "slug": {"$nin": list(selected_slugs)},
        }
        related_articles.extend(
            await _fetch_related_article_cards(
                db,
                fallback_filter,
                category_lookup,
                RELATED_ARTICLE_LIMIT - len(related_articles),
            )
        )

    return related_articles


async def _fetch_related_article_cards(
    db: Any,
    article_filter: dict[str, Any],
    category_lookup: dict[str, str],
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []

    cursor = (
        db[ARTICLE_COLLECTION]
        .find(article_filter)
        .sort(
            [
                ("is_featured", DESCENDING),
                ("published_at", DESCENDING),
                ("created_at", DESCENDING),
            ]
        )
        .limit(limit)
    )

    return [
        _article_to_card(ArticleRead.model_validate(document), category_lookup)
        async for document in cursor
    ]


def _article_to_card(
    article: ArticleRead,
    category_lookup: dict[str, str],
) -> dict[str, Any]:
    published_at = _format_date(article.published_at)
    reading_time = calculate_reading_time(article.content)

    return {
        "title": article.title,
        "slug": article.slug,
        "url": f"/articles/{article.slug}",
        "excerpt": article.excerpt,
        "category": category_lookup.get(article.category_id or "", "Article"),
        "category_url": (
            f"/articles?{urlencode({'category': article.category_id})}"
            if article.category_id
            else "/articles"
        ),
        "read_time": reading_time.label,
        "read_time_minutes": reading_time.minutes,
        "word_count": reading_time.word_count,
        "word_count_label": _format_word_count(reading_time.word_count),
        "cover_image": article.cover_image or "/static/images/articles/editorial-default.svg",
        "image_alt": article.title,
        "author": article.author,
        "published_label": published_at,
        "views": article.views,
        "tags": article.tags,
        "tag_links": [
            {
                "name": tag,
                "url": f"/articles?{urlencode({'tag': tag})}",
            }
            for tag in article.tags
        ],
    }


def article_to_card_context(
    article: ArticleRead,
    category_lookup: dict[str, str],
) -> dict[str, Any]:
    return _article_to_card(article, category_lookup)


def _article_to_detail(
    article: ArticleRead,
    category_lookup: dict[str, str],
) -> dict[str, Any]:
    card = _article_to_card(article, category_lookup)
    paragraphs = [
        paragraph.strip()
        for paragraph in article.content.split("\n\n")
        if paragraph.strip()
    ]

    return {
        **card,
        "content": article.content,
        "content_paragraphs": paragraphs,
        "seo_title": article.seo_title or article.title,
        "seo_description": article.seo_description or article.excerpt,
        "published_iso": article.published_at.isoformat() if article.published_at else "",
        "updated_iso": article.updated_at.isoformat() if article.updated_at else "",
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


def _format_word_count(word_count: int) -> str:
    if word_count == 1:
        return "1 word"

    return f"{word_count:,} words"


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
