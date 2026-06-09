from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.tag import TAG_COLLECTION
from app.schemas.article import ArticleQueryParams
from app.services.article_page_service import article_to_card_context
from app.services.article_service import ArticleService


SEARCH_RESULTS_PER_PAGE = 6

SEARCH_SORT_OPTIONS: tuple[dict[str, str], ...] = (
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


async def get_search_page_context(
    *,
    page: int,
    query: str | None,
    category: str | None,
    tag: str | None,
    sort: str,
) -> dict[str, Any]:
    try:
        db = get_database()
        clean_query = _clean_query(query)
        is_query_too_short = _is_query_too_short(query, clean_query)
        sort_option = _resolve_sort_option(sort)
        category_filter = _clean_optional_slug(category)
        base_tag_options = await _get_tag_options(db)
        tag_filter = _resolve_tag_filter(tag, base_tag_options)
        tag_filter_name = tag_filter["name"] if tag_filter else None
        tag_filter_slug = tag_filter["slug"] if tag_filter else None

        category_options = await _get_category_options(
            db,
            search=clean_query,
            active_tag=tag_filter_name,
        )
        tag_options = await _get_tag_options(
            db,
            search=clean_query,
            category=category_filter,
        )

        article_list = None
        articles = []
        if clean_query and not is_query_too_short:
            article_query = ArticleQueryParams(
                page=page,
                per_page=SEARCH_RESULTS_PER_PAGE,
                status=ARTICLE_STATUS_PUBLISHED,
                category_id=category_filter,
                tag=tag_filter_name,
                search=clean_query,
                sort_by=sort_option["sort_by"],
                sort_direction=sort_option["sort_direction"],
            )
            article_list = await ArticleService(database=db).list_articles(article_query)
            category_lookup = {
                item["slug"]: item["name"]
                for item in category_options
            }
            tag_lookup = {
                item["name"].lower(): item["slug"]
                for item in base_tag_options
            }
            articles = [
                article_to_card_context(article, category_lookup, tag_lookup)
                for article in article_list.items
            ]

        total = article_list.total if article_list else 0
        current_page = article_list.page if article_list else 1
        total_pages = article_list.total_pages if article_list else 0
        per_page = article_list.per_page if article_list else SEARCH_RESULTS_PER_PAGE

        return {
            "articles": articles,
            "result_count": total,
            "search_query": clean_query or "",
            "raw_search_query": str(query or ""),
            "is_query_too_short": is_query_too_short,
            "has_search_query": bool(clean_query),
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "total_items": total,
                "per_page": per_page,
                "url_template": _search_url_template(
                    query=clean_query,
                    category=category_filter,
                    tag=tag_filter_slug,
                    sort=sort_option["value"],
                ),
                "aria_label": "Search result pages",
            },
            "category_filters": _category_filters(
                category_options,
                query=clean_query,
                active_category=category_filter,
                active_tag=tag_filter_slug,
                sort=sort_option["value"],
            ),
            "tag_filters": _tag_filters(
                tag_options,
                query=clean_query,
                active_tag=tag_filter_slug,
                category=category_filter,
                sort=sort_option["value"],
            ),
            "sort_options": _mark_active_filter(
                list(SEARCH_SORT_OPTIONS),
                sort_option["value"],
            ),
            "active_category": _category_name(category_options, category_filter),
            "active_category_slug": category_filter,
            "active_tag": tag_filter["name"] if tag_filter else None,
            "active_tag_slug": tag_filter_slug,
            "active_sort": sort_option["label"],
            "is_filter_active": bool(
                category_filter
                or tag_filter_slug
                or sort_option["value"] != "newest"
            ),
            "categories": [
                item["name"]
                for item in category_options
            ],
            "is_database_available": True,
        }
    except (RuntimeError, PyMongoError):
        return _empty_search_context(query)


async def _get_category_options(
    db: Any,
    *,
    search: str | None = None,
    active_tag: str | None = None,
) -> list[dict[str, Any]]:
    categories = []
    cursor = db.categories.find({}, {"_id": 0}).sort("name", ASCENDING)

    async for category in cursor:
        slug = str(category.get("slug", "")).strip()
        name = str(category.get("name", "")).strip()
        if not slug or not name:
            continue

        article_filter = _base_article_filter(search=search, tag=active_tag)
        article_filter["category_id"] = slug
        total = await db[ARTICLE_COLLECTION].count_documents(article_filter)
        categories.append(
            {
                "name": name,
                "slug": slug,
                "value": slug,
                "total": total,
            }
        )

    return categories


async def _get_tag_options(
    db: Any,
    *,
    search: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    tags = []
    cursor = db[TAG_COLLECTION].find({}, {"_id": 0}).sort("name", ASCENDING)

    async for tag in cursor:
        slug = str(tag.get("slug", "")).strip()
        name = str(tag.get("name", "")).strip()
        if not slug or not name:
            continue

        article_filter = _base_article_filter(search=search, category=category)
        article_filter["tags"] = name
        total = await db[ARTICLE_COLLECTION].count_documents(article_filter)
        tags.append(
            {
                "name": name,
                "slug": slug,
                "value": slug,
                "total": total,
            }
        )

    return tags


def _base_article_filter(
    *,
    search: str | None = None,
    category: str | None = None,
    tag: str | None = None,
) -> dict[str, Any]:
    article_filter: dict[str, Any] = {"status": ARTICLE_STATUS_PUBLISHED}
    if search:
        article_filter["$text"] = {"$search": search}
    if category:
        article_filter["category_id"] = category
    if tag:
        article_filter["tags"] = tag

    return article_filter


def _resolve_sort_option(sort: str) -> dict[str, Any]:
    clean_sort = str(sort or "").strip().lower()

    for option in SEARCH_SORT_OPTIONS:
        if option["value"] == clean_sort:
            return {
                "label": option["label"],
                "value": option["value"],
                "sort_by": option["sort_by"],
                "sort_direction": option["sort_direction"],
            }

    default_option = SEARCH_SORT_OPTIONS[0]
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


def _category_filters(
    options: list[dict[str, Any]],
    *,
    query: str | None,
    active_category: str | None,
    active_tag: str | None,
    sort: str,
) -> list[dict[str, Any]]:
    return [
        {
            **option,
            "is_active": option.get("value") == active_category,
            "url": _search_filter_url(
                query=query,
                category=option.get("slug"),
                tag=active_tag,
                sort=sort,
            ),
        }
        for option in options
    ]


def _tag_filters(
    options: list[dict[str, Any]],
    *,
    query: str | None,
    active_tag: str | None,
    category: str | None,
    sort: str,
) -> list[dict[str, Any]]:
    return [
        {
            **option,
            "is_active": option.get("value") == active_tag,
            "url": _search_filter_url(
                query=query,
                category=category,
                tag=option.get("slug"),
                sort=sort,
            ),
        }
        for option in options
    ]


def _search_url_template(
    *,
    query: str | None,
    category: str | None,
    tag: str | None,
    sort: str,
) -> str:
    params = {"page": "__page__", "sort": sort}
    if query:
        params["q"] = query
    if category:
        params["category"] = category
    if tag:
        params["tag"] = tag

    return f"/search?{urlencode(params)}".replace("__page__", "{page}")


def _search_filter_url(
    *,
    query: str | None,
    category: str | None,
    tag: str | None,
    sort: str,
) -> str:
    params = {"sort": sort}
    if query:
        params["q"] = query
    if category:
        params["category"] = category
    if tag:
        params["tag"] = tag

    return f"/search?{urlencode(params)}"


def _category_name(
    options: list[dict[str, Any]],
    category: str | None,
) -> str | None:
    for option in options:
        if option.get("slug") == category:
            return str(option.get("name"))

    return None


def _resolve_tag_filter(
    value: str | None,
    tag_options: list[dict[str, Any]],
) -> dict[str, str] | None:
    clean_value = _clean_optional_tag(value)
    if clean_value is None:
        return None

    normalized_value = clean_value.lower()
    for tag in tag_options:
        slug = str(tag.get("slug", "")).lower()
        name = str(tag.get("name", ""))
        if normalized_value in {slug, name.lower()}:
            return {"name": name, "slug": slug}

    return {"name": clean_value, "slug": normalized_value}


def _clean_query(value: str | None) -> str | None:
    if value is None:
        return None

    clean_value = value.strip()
    return clean_value if len(clean_value) >= 2 else None


def _is_query_too_short(
    raw_value: str | None,
    clean_value: str | None,
) -> bool:
    return bool(str(raw_value or "").strip()) and clean_value is None


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


def _empty_search_context(query: str | None = None) -> dict[str, Any]:
    clean_query = _clean_query(query)

    return {
        "articles": [],
        "result_count": 0,
        "search_query": clean_query or "",
        "raw_search_query": str(query or ""),
        "is_query_too_short": _is_query_too_short(query, clean_query),
        "has_search_query": bool(clean_query),
        "pagination": {
            "current_page": 1,
            "total_pages": 0,
            "total_items": 0,
            "per_page": SEARCH_RESULTS_PER_PAGE,
            "url_template": "/search?page={page}",
            "aria_label": "Search result pages",
        },
        "category_filters": [],
        "tag_filters": [],
        "sort_options": _mark_active_filter(list(SEARCH_SORT_OPTIONS), "newest"),
        "active_category": None,
        "active_category_slug": None,
        "active_tag": None,
        "active_tag_slug": None,
        "active_sort": "Newest",
        "is_filter_active": False,
        "categories": [],
        "is_database_available": False,
    }
