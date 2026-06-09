from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.schemas.article import ArticleQueryParams
from app.schemas.category import CategoryRead
from app.services.article_page_service import article_to_card_context
from app.services.article_service import ArticleService
from app.services.category_service import CategoryService


CATEGORY_LISTING_PER_PAGE = 9
CATEGORY_DETAIL_PER_PAGE = 6

CATEGORY_SORT_OPTIONS: tuple[dict[str, Any], ...] = (
    {
        "label": "Name A-Z",
        "value": "name_asc",
        "sort": {"name": 1, "_id": 1},
    },
    {
        "label": "Name Z-A",
        "value": "name_desc",
        "sort": {"name": -1, "_id": -1},
    },
    {
        "label": "Most articles",
        "value": "popular",
        "sort": {"article_count": -1, "name": 1, "_id": 1},
    },
    {
        "label": "Slug A-Z",
        "value": "slug_asc",
        "sort": {"slug": 1, "_id": 1},
    },
)

CATEGORY_ARTICLE_STATE_OPTIONS: tuple[dict[str, str], ...] = (
    {"label": "All", "value": "all"},
    {"label": "With articles", "value": "active"},
    {"label": "Empty", "value": "empty"},
)


async def get_category_listing_context(
    *,
    page: int,
    search: str | None = None,
    article_state: str = "all",
    sort: str = "name_asc",
) -> dict[str, Any]:
    try:
        db = get_database()
        clean_search = _clean_search(search)
        state_option = _resolve_article_state_option(article_state)
        sort_option = _resolve_sort_option(sort)
        category_page = await _get_filtered_category_page(
            db=db,
            page=page,
            search=clean_search,
            article_state=state_option["value"],
            sort_option=sort_option,
        )
        categories = [
            _category_to_card(category, category["article_count"])
            for category in category_page["items"]
        ]

        return {
            "categories": await _get_category_names(db),
            "category_cards": categories,
            "category_count": category_page["total"],
            "total_published_articles": category_page["article_total"],
            "pagination": {
                "current_page": page,
                "total_pages": _total_pages(
                    category_page["total"],
                    CATEGORY_LISTING_PER_PAGE,
                ),
                "total_items": category_page["total"],
                "per_page": CATEGORY_LISTING_PER_PAGE,
                "url_template": _category_pagination_url_template(
                    search=clean_search,
                    article_state=state_option["value"],
                    sort=sort_option["value"],
                ),
                "aria_label": "Category pages",
            },
            "article_state_filters": _article_state_filters(
                search=clean_search,
                active_state=state_option["value"],
                sort=sort_option["value"],
                state_counts=category_page["state_counts"],
            ),
            "sort_options": _mark_active_filter(
                list(CATEGORY_SORT_OPTIONS),
                sort_option["value"],
            ),
            "active_search": clean_search or "",
            "active_article_state": state_option["value"],
            "active_article_state_label": state_option["label"],
            "active_sort": sort_option["label"],
            "is_category_filter_active": bool(
                clean_search or state_option["value"] != "all"
            ),
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


async def _get_filtered_category_page(
    *,
    db: Any,
    page: int,
    search: str | None,
    article_state: str,
    sort_option: dict[str, Any],
) -> dict[str, Any]:
    skip = (page - 1) * CATEGORY_LISTING_PER_PAGE
    pipeline = [
        {"$match": _category_search_match(search)},
        {
            "$lookup": {
                "from": ARTICLE_COLLECTION,
                "let": {"category_slug": "$slug"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$category_id", "$$category_slug"]},
                                    {"$eq": ["$status", ARTICLE_STATUS_PUBLISHED]},
                                ]
                            }
                        }
                    },
                    {"$count": "total"},
                ],
                "as": "article_stats",
            }
        },
        {
            "$addFields": {
                "article_count": {
                    "$ifNull": [{"$arrayElemAt": ["$article_stats.total", 0]}, 0]
                }
            }
        },
        {
            "$facet": {
                "items": [
                    *_article_state_match_pipeline(article_state),
                    {"$sort": sort_option["sort"]},
                    {"$skip": skip},
                    {"$limit": CATEGORY_LISTING_PER_PAGE},
                ],
                "summary": [
                    *_article_state_match_pipeline(article_state),
                    {
                        "$group": {
                            "_id": None,
                            "total": {"$sum": 1},
                            "article_total": {"$sum": "$article_count"},
                        }
                    },
                ],
                "state_counts": [
                    {
                        "$group": {
                            "_id": None,
                            "all": {"$sum": 1},
                            "active": {
                                "$sum": {
                                    "$cond": [{"$gt": ["$article_count", 0]}, 1, 0]
                                }
                            },
                            "empty": {
                                "$sum": {
                                    "$cond": [{"$eq": ["$article_count", 0]}, 1, 0]
                                }
                            },
                        }
                    },
                ],
            }
        },
    ]
    result = await db.categories.aggregate(pipeline).to_list(length=1)
    payload = result[0] if result else {}
    summary = _first_item(payload.get("summary", []))
    state_counts = _first_item(payload.get("state_counts", []))

    return {
        "items": payload.get("items", []),
        "total": int(summary.get("total", 0)),
        "article_total": int(summary.get("article_total", 0)),
        "state_counts": {
            "all": int(state_counts.get("all", 0)),
            "active": int(state_counts.get("active", 0)),
            "empty": int(state_counts.get("empty", 0)),
        },
    }


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
        "description": category_data["description"]
        or "A focused collection of articles from this editorial lane.",
        "image": category_data["image"]
        or "/static/images/articles/editorial-default.svg",
        "image_alt": f"{category_data['name']} category",
        "article_count": article_count,
        "article_count_label": _format_article_count(article_count),
        "category_url": f"/categories/{category_data['slug']}",
        "articles_url": f"/articles?{urlencode({'category': category_data['slug']})}",
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


def _article_state_filters(
    *,
    search: str | None,
    active_state: str,
    sort: str,
    state_counts: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        {
            **option,
            "count": state_counts.get(option["value"], 0),
            "is_active": option["value"] == active_state,
            "url": _category_filter_url(
                search=search,
                article_state=option["value"],
                sort=sort,
            ),
        }
        for option in CATEGORY_ARTICLE_STATE_OPTIONS
    ]


def _mark_active_filter(
    options: list[dict[str, Any]],
    active_value: str,
) -> list[dict[str, Any]]:
    return [
        {
            **option,
            "is_active": option.get("value") == active_value,
        }
        for option in options
    ]


def _resolve_article_state_option(article_state: str) -> dict[str, str]:
    clean_state = str(article_state or "").strip().lower()
    for option in CATEGORY_ARTICLE_STATE_OPTIONS:
        if option["value"] == clean_state:
            return dict(option)

    return dict(CATEGORY_ARTICLE_STATE_OPTIONS[0])


def _resolve_sort_option(sort: str) -> dict[str, Any]:
    clean_sort = str(sort or "").strip().lower()
    for option in CATEGORY_SORT_OPTIONS:
        if option["value"] == clean_sort:
            return dict(option)

    return dict(CATEGORY_SORT_OPTIONS[0])


def _category_search_match(search: str | None) -> dict[str, Any]:
    if not search:
        return {}

    escaped_search = re.escape(search)
    return {
        "$or": [
            {"name": {"$regex": escaped_search, "$options": "i"}},
            {"slug": {"$regex": escaped_search, "$options": "i"}},
            {"description": {"$regex": escaped_search, "$options": "i"}},
        ]
    }


def _article_state_match_pipeline(article_state: str) -> list[dict[str, Any]]:
    if article_state == "active":
        return [{"$match": {"article_count": {"$gt": 0}}}]
    if article_state == "empty":
        return [{"$match": {"article_count": 0}}]

    return []


def _category_pagination_url_template(
    *,
    search: str | None,
    article_state: str,
    sort: str,
) -> str:
    params = {"page": "__page__", "sort": sort}
    if search:
        params["search"] = search
    if article_state != "all":
        params["article_state"] = article_state

    return f"/categories?{urlencode(params)}".replace("__page__", "{page}")


def _category_filter_url(
    *,
    search: str | None,
    article_state: str,
    sort: str,
) -> str:
    params = {"sort": sort}
    if search:
        params["search"] = search
    if article_state != "all":
        params["article_state"] = article_state

    return f"/categories?{urlencode(params)}" if params else "/categories"


def _category_read_context(category: CategoryRead | dict[str, Any]) -> dict[str, Any]:
    if isinstance(category, CategoryRead):
        return {
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "image": category.image,
        }

    return {
        "name": str(category.get("name", "")).strip(),
        "slug": str(category.get("slug", "")).strip(),
        "description": category.get("description"),
        "image": category.get("image"),
    }


def _clean_search(search: str | None) -> str | None:
    if search is None:
        return None

    clean_search = " ".join(str(search).split())
    return clean_search or None


def _first_item(items: list[dict[str, Any]]) -> dict[str, Any]:
    return items[0] if items else {}


def _total_pages(total: int, per_page: int) -> int:
    if total <= 0:
        return 0

    return (total + per_page - 1) // per_page


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
        "article_state_filters": _article_state_filters(
            search=None,
            active_state="all",
            sort="name_asc",
            state_counts={"all": 0, "active": 0, "empty": 0},
        ),
        "sort_options": _mark_active_filter(list(CATEGORY_SORT_OPTIONS), "name_asc"),
        "active_search": "",
        "active_article_state": "all",
        "active_article_state_label": "All",
        "active_sort": "Name A-Z",
        "is_category_filter_active": False,
    }
