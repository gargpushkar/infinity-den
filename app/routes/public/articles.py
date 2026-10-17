from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi import status as http_status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.config.settings import settings
from app.routes.public.form_pages import FORM_EXPIRED, TOO_MANY_ATTEMPTS, field_errors, safe_next
from app.routes.public.seo import article_schema, social_image_url
from app.schemas.comment import CommentInput
from app.services.article_conversation_service import get_conversation_context, published_article_id
from app.services.article_page_service import (
    get_article_detail_context,
    get_article_listing_context,
)
from app.services.bookmark_service import BookmarkService
from app.services.comment_service import CommentService
from app.services.member_session import (
    form_csrf_is_valid,
    form_csrf_token,
    get_current_member,
    set_form_csrf_cookie,
)
from app.services.nav_service import get_nav_context
from app.utils.forms import read_form
from app.utils.rate_limit import member_comment_limiter


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

ARTICLE_SLUG = Path(min_length=3, max_length=180)
COMMENT_NOTICES = {
    "posted": "Your comment is live.",
    "deleted": "Your comment was removed.",
}


@router.get("/articles")
async def article_listing(
    request: Request,
    page: int = Query(default=1, ge=1),
    category: str | None = Query(default=None, max_length=120),
    tag: str | None = Query(default=None, max_length=64),
    sort: str = Query(default="newest", max_length=40),
    format: str | None = Query(default=None, max_length=20),
):
    nav_context = await get_nav_context(request)
    listing_context = await get_article_listing_context(
        page=page,
        category=category,
        tag=tag,
        sort=sort,
        article_format=format,
    )

    return templates.TemplateResponse(
        request,
        "pages/articles.html",
        {
            **nav_context,
            "app_name": settings.app_name,
            "page_title": "Articles",
            **_breadcrumb_context(
                request,
                _article_listing_breadcrumbs(listing_context),
            ),
            **listing_context,
        },
    )


@router.get("/articles/{article_slug}")
async def article_detail(request: Request, article_slug: str = ARTICLE_SLUG, notice: str = ""):
    return await _render_article(request, article_slug, notice=COMMENT_NOTICES.get(notice))


@router.post("/articles/{article_slug}/comments")
async def post_comment(request: Request, article_slug: str = ARTICLE_SLUG):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next=/articles/{article_slug}%23comments", status_code=303)

    form = await read_form(request)
    values = {"body": form.get("body", "")}
    if not form_csrf_is_valid(request, form):
        return await _render_article(request, article_slug, values=values, error=FORM_EXPIRED, status_code=400)
    article_id = await published_article_id(article_slug)
    if article_id is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Article was not found.")
    if not member_comment_limiter.allow(member.id):
        return await _render_article(request, article_slug, values=values, error=TOO_MANY_ATTEMPTS, status_code=429)

    try:
        payload = CommentInput(body=values["body"])
    except ValidationError as exc:
        return await _render_article(
            request, article_slug, values=values, field_errors=field_errors(exc), status_code=422
        )

    await CommentService().add(article_id, member, payload)
    return RedirectResponse(f"/articles/{article_slug}?notice=posted#comments", status_code=303)


@router.post("/articles/{article_slug}/comments/{comment_id}/delete")
async def delete_comment(request: Request, article_slug: str = ARTICLE_SLUG, comment_id: str = Path(max_length=40)):
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next=/articles/{article_slug}", status_code=303)

    form = await read_form(request)
    if not form_csrf_is_valid(request, form):
        return await _render_article(request, article_slug, error=FORM_EXPIRED, status_code=400)
    await CommentService().delete_own(comment_id, member)
    return RedirectResponse(f"/articles/{article_slug}?notice=deleted#comments", status_code=303)


@router.post("/articles/{article_slug}/bookmark")
async def bookmark(request: Request, article_slug: str = ARTICLE_SLUG):
    """Save or remove a piece. `next` returns the reader to /saved or the article."""
    article_url = f"/articles/{article_slug}"
    member = await get_current_member(request)
    if member is None:
        return RedirectResponse(f"/login?next={article_url}", status_code=303)

    form = await read_form(request)
    back = safe_next(form.get("next", "")) or article_url
    if not form_csrf_is_valid(request, form):
        return RedirectResponse(back, status_code=303)
    article_id = await published_article_id(article_slug)
    if article_id is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Article was not found.")

    service = BookmarkService()
    if form.get("action") == "remove":
        await service.remove(member, article_id)
    else:
        await service.save(member, article_id)
    return RedirectResponse(back, status_code=303)


async def _render_article(
    request: Request,
    article_slug: str,
    *,
    values: dict[str, str] | None = None,
    field_errors: dict[str, str] | None = None,
    error: str | None = None,
    notice: str | None = None,
    status_code: int = 200,
):
    # A form re-shown after an error is not a new read, so it does not count a view.
    detail_context = await get_article_detail_context(article_slug, record_view=request.method == "GET")
    if detail_context is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Article was not found.",
        )

    article = detail_context["article"]
    member = await get_current_member(request)
    breadcrumbs = _article_detail_breadcrumbs(article)
    csrf_token = form_csrf_token(request)

    response = templates.TemplateResponse(
        request,
        "pages/article_detail.html",
        {
            **await get_nav_context(request),
            "app_name": settings.app_name,
            "page_title": article["seo_title"],
            **_article_seo_context(request, article),
            **_breadcrumb_context(request, breadcrumbs),
            "share_actions": _article_share_actions(request, article),
            **detail_context,
            **await get_conversation_context(article["id"], member),
            "signed_in": member is not None,
            "csrf_token": csrf_token,
            "values": values or {},
            "field_errors": field_errors or {},
            "comment_error": error,
            "comment_notice": notice,
        },
        status_code=status_code,
    )
    set_form_csrf_cookie(response, csrf_token)
    return response


def _article_listing_breadcrumbs(context: dict[str, Any]) -> list[dict[str, Any]]:
    active_category = context.get("active_category")
    active_tag = context.get("active_tag")
    breadcrumbs: list[dict[str, Any]] = [
        {"label": "Home", "url": "/", "is_current": False},
    ]

    if active_category or active_tag:
        breadcrumbs.append(
            {"label": "Articles", "url": "/articles", "is_current": False}
        )
        if active_category:
            breadcrumbs.append(
                {
                    "label": str(active_category),
                    "url": None if not active_tag else _category_url(context),
                    "is_current": not active_tag,
                }
            )
        if active_tag:
            breadcrumbs.append(
                {
                    "label": f"Tag: {active_tag}",
                    "url": None,
                    "is_current": True,
                }
            )
    else:
        breadcrumbs.append({"label": "Articles", "url": None, "is_current": True})

    return breadcrumbs


def _article_detail_breadcrumbs(article: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"label": "Home", "url": "/", "is_current": False},
        {"label": "Articles", "url": "/articles", "is_current": False},
        {
            "label": article["category"],
            "url": article["category_url"],
            "is_current": False,
        },
        {"label": article["title"], "url": None, "is_current": True},
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


def _category_url(context: dict[str, Any]) -> str:
    active_category = context.get("active_category")
    for category in context.get("category_filters", []):
        if category.get("name") == active_category:
            return str(category["url"])

    return "/articles"


def _article_seo_context(request: Request, article: dict) -> dict[str, Any]:
    canonical_url = str(
        request.url_for("article_detail", article_slug=article["slug"])
    )
    seo_image = social_image_url(request, article.get("cover_image", ""))

    return {
        "seo_title": article["seo_title"],
        "seo_description": article["seo_description"],
        "canonical_url": canonical_url,
        "open_graph_type": "article",
        "seo_image": seo_image,
        "seo_image_alt": article.get("image_alt", article["title"]),
        "page_schema": article_schema(request, article, canonical_url, seo_image),
    }


def _article_share_actions(
    request: Request,
    article: dict[str, Any],
) -> list[dict[str, str]]:
    article_url = str(request.url_for("article_detail", article_slug=article["slug"]))
    article_title = str(article["title"])
    email_body = f"{article['excerpt']}\n\nRead it here: {article_url}"

    return [
        {
            "label": "X",
            "name": "Share on X",
            "url": "https://twitter.com/intent/tweet?"
            + urlencode({"url": article_url, "text": article_title}),
        },
        {
            "label": "in",
            "name": "Share on LinkedIn",
            "url": "https://www.linkedin.com/sharing/share-offsite/?"
            + urlencode({"url": article_url}),
        },
        {
            "label": "f",
            "name": "Share on Facebook",
            "url": "https://www.facebook.com/sharer/sharer.php?"
            + urlencode({"u": article_url}),
        },
        {
            "label": "@",
            "name": "Share by email",
            "url": "mailto:?"
            + urlencode({"subject": article_title, "body": email_body}),
        },
        {
            "label": "cp",
            "name": "Copy article link",
            "url": article_url,
            "action": "copy",
        },
    ]



def _absolute_site_url(request: Request, url: str) -> str:
    clean_url = str(url or "").strip()
    if clean_url.startswith(("http://", "https://")):
        return clean_url
    if clean_url.startswith("/"):
        return f"{str(request.base_url).rstrip('/')}{clean_url}"

    return f"{str(request.base_url).rstrip('/')}/{clean_url}"
