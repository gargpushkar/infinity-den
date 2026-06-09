from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates

from app.config.settings import settings
from app.services.category_page_service import get_category_listing_context


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/categories")
async def category_listing(
    request: Request,
    page: int = Query(default=1, ge=1),
):
    listing_context = await get_category_listing_context(page=page)

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


def _category_listing_breadcrumbs() -> list[dict[str, Any]]:
    return [
        {"label": "Home", "url": "/", "is_current": False},
        {"label": "Categories", "url": None, "is_current": True},
    ]


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
