from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates

from app.config.settings import settings
from app.services.search_page_service import get_search_page_context


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/search")
async def search_page(
    request: Request,
    q: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    category: str | None = Query(default=None, max_length=120),
    tag: str | None = Query(default=None, max_length=64),
    sort: str = Query(default="newest", max_length=40),
):
    search_context = await get_search_page_context(
        page=page,
        query=q,
        category=category,
        tag=tag,
        sort=sort,
    )

    return templates.TemplateResponse(
        request,
        "pages/search.html",
        {
            "app_name": settings.app_name,
            "page_title": "Search",
            **_search_seo_context(request, search_context),
            **_breadcrumb_context(request, _search_breadcrumbs(search_context)),
            **search_context,
        },
    )


def _search_breadcrumbs(context: dict[str, Any]) -> list[dict[str, Any]]:
    breadcrumbs: list[dict[str, Any]] = [
        {"label": "Home", "url": "/", "is_current": False},
    ]
    query = context.get("search_query")

    if query:
        breadcrumbs.append({"label": "Search", "url": "/search", "is_current": False})
        breadcrumbs.append(
            {"label": f"Results for {query}", "url": None, "is_current": True}
        )
    else:
        breadcrumbs.append({"label": "Search", "url": None, "is_current": True})

    return breadcrumbs


def _search_seo_context(
    request: Request,
    context: dict[str, Any],
) -> dict[str, str]:
    query = str(context.get("search_query") or "").strip()
    canonical_params = {}
    if query:
        canonical_params["q"] = query
    if context.get("active_category_slug"):
        canonical_params["category"] = context["active_category_slug"]
    if context.get("active_tag_slug"):
        canonical_params["tag"] = context["active_tag_slug"]

    canonical_url = str(request.url_for("search_page"))
    if canonical_params:
        canonical_url = f"{canonical_url}?{urlencode(canonical_params)}"

    title = f"Search results for {query}" if query else "Search"

    return {
        "seo_title": title,
        "seo_description": (
            f"Search {settings.app_name} articles by keyword, category, and tag."
        ),
        "canonical_url": canonical_url,
        "open_graph_type": "website",
        "twitter_card": "summary",
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
