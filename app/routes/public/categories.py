from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi import status as http_status
from fastapi.templating import Jinja2Templates

from app.config.settings import settings
from app.services.category_page_service import (
    get_category_detail_context,
    get_category_listing_context,
)


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/categories")
async def category_listing(
    request: Request,
    page: int = Query(default=1, ge=1),
    search: str | None = Query(default=None, max_length=120),
    article_state: str = Query(default="all", max_length=20),
    sort: str = Query(default="name_asc", max_length=40),
):
    listing_context = await get_category_listing_context(
        page=page,
        search=search,
        article_state=article_state,
        sort=sort,
    )

    return templates.TemplateResponse(
        request,
        "pages/categories.html",
        {
            "app_name": settings.app_name,
            "page_title": "Categories",
            "seo_title": "Categories",
            "seo_description": (
                f"Browse {settings.app_name} topic hubs by category and explore "
                "published article collections."
            ),
            **_breadcrumb_context(request, _category_listing_breadcrumbs()),
            **listing_context,
        },
    )


@router.get("/categories/{category_slug}")
async def category_detail(
    request: Request,
    category_slug: str = Path(min_length=3, max_length=120),
    page: int = Query(default=1, ge=1),
):
    detail_context = await get_category_detail_context(
        category_slug=category_slug,
        page=page,
    )
    if detail_context is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Category was not found.",
        )

    category = detail_context["category"]

    return templates.TemplateResponse(
        request,
        "pages/category_detail.html",
        {
            "app_name": settings.app_name,
            "page_title": category["seo_title"],
            **_category_seo_context(request, category),
            **_breadcrumb_context(request, _category_detail_breadcrumbs(category)),
            **detail_context,
        },
    )


def _category_listing_breadcrumbs() -> list[dict[str, Any]]:
    return [
        {"label": "Home", "url": "/", "is_current": False},
        {"label": "Categories", "url": None, "is_current": True},
    ]


def _category_detail_breadcrumbs(category: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"label": "Home", "url": "/", "is_current": False},
        {"label": "Categories", "url": "/categories", "is_current": False},
        {"label": category["name"], "url": None, "is_current": True},
    ]


def _category_seo_context(
    request: Request,
    category: dict[str, Any],
) -> dict[str, str]:
    canonical_url = str(
        request.url_for("category_detail", category_slug=category["slug"])
    )
    seo_image = _absolute_image_url(request, category.get("image", ""))

    return {
        "seo_title": category["seo_title"],
        "seo_description": category["seo_description"],
        "canonical_url": canonical_url,
        "open_graph_type": "website",
        "seo_image": seo_image,
        "seo_image_alt": category.get("image_alt", category["name"]),
        "twitter_card": "summary_large_image" if seo_image else "summary",
    }


def _breadcrumb_context(
    request: Request,
    breadcrumbs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "breadcrumbs": breadcrumbs,
        "breadcrumb_schema": _breadcrumb_schema(request, breadcrumbs),
    }


def _breadcrumb_schema(
    request: Request,
    breadcrumbs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": breadcrumb["label"],
                **(
                    {"item": _absolute_site_url(request, breadcrumb["url"])}
                    if breadcrumb.get("url")
                    else {}
                ),
            }
            for index, breadcrumb in enumerate(breadcrumbs, start=1)
        ],
    }


def _absolute_site_url(request: Request, url: str) -> str:
    clean_url = str(url or "").strip()
    if clean_url.startswith(("http://", "https://")):
        return clean_url
    if clean_url.startswith("/"):
        return f"{str(request.base_url).rstrip('/')}{clean_url}"

    return f"{str(request.base_url).rstrip('/')}/{clean_url}"


def _absolute_image_url(request: Request, image_url: str) -> str:
    clean_image_url = str(image_url or "").strip()
    if not clean_image_url:
        return ""
    if clean_image_url.startswith(("http://", "https://")):
        return clean_image_url
    if clean_image_url.startswith("/static/"):
        return str(
            request.url_for(
                "static",
                path=clean_image_url.removeprefix("/static/"),
            )
        )
    if clean_image_url.startswith("/"):
        return f"{str(request.base_url).rstrip('/')}{clean_image_url}"

    return f"{str(request.base_url).rstrip('/')}/{clean_image_url}"
