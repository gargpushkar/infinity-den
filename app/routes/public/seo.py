"""robots.txt, sitemap.xml, structured data, and social preview images."""

from typing import Any
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse
from pymongo.errors import PyMongoError

from app.config.settings import settings
from app.services.sitemap_service import SECTION_PAGES, sitemap_entries


router = APIRouter()

TAGLINE = "A universe of ideas. A community of minds."
PRIVATE_PATHS = ("/admin", "/api/", "/account", "/write", "/saved", "/report", "/login", "/join", "/logout",
                 "/forgot-password", "/reset-password")


def site_url(request: Request) -> str:
    # ponytail: the request's own origin. Behind a proxy, run uvicorn with
    # --proxy-headers so this is the public https:// address.
    return str(request.base_url).rstrip("/")


@router.get("/robots.txt", include_in_schema=False)
async def robots_txt(request: Request) -> PlainTextResponse:
    lines = ["User-agent: *", *(f"Disallow: {path}" for path in PRIVATE_PATHS), "", f"Sitemap: {site_url(request)}/sitemap.xml", ""]
    return PlainTextResponse("\n".join(lines), headers={"Cache-Control": "public, max-age=86400"})


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml(request: Request) -> Response:
    try:
        entries = await sitemap_entries()
    except (RuntimeError, PyMongoError):
        entries = [(path, None) for path in SECTION_PAGES]
    base = site_url(request)
    urls = "".join(
        f"<url><loc>{escape(base + path)}</loc>{f'<lastmod>{lastmod}</lastmod>' if lastmod else ''}</url>"
        for path, lastmod in entries
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return Response(xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})


def social_image_url(request: Request, image_url: str | None) -> str:
    """An absolute URL for og:image, or "" to use the site's default preview.

    Facebook, LinkedIn and X do not show SVG previews, so generated covers
    (and any other SVG) fall back to the branded PNG in the base layout.
    """
    clean_image_url = str(image_url or "").strip()
    if not clean_image_url or clean_image_url.split("?", 1)[0].endswith(".svg"):
        return ""
    if clean_image_url.startswith(("http://", "https://")):
        return clean_image_url
    if clean_image_url.startswith("/static/"):
        return str(request.url_for("static", path=clean_image_url.removeprefix("/static/")))
    return f"{str(request.base_url).rstrip('/')}/{clean_image_url.lstrip('/')}"


def _logo(request: Request) -> dict[str, str]:
    return {"@type": "ImageObject", "url": str(request.url_for("static", path="icons/icon-512.png"))}


def article_schema(request: Request, article: dict[str, Any], canonical_url: str, image_url: str) -> dict[str, Any]:
    """schema.org Article for search engines. Member authors link to their profile."""
    author: dict[str, Any] = {"@type": "Person", "name": article["author"]}
    if article.get("author_url"):
        author["url"] = site_url(request) + article["author_url"]
    schema: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article["title"][:110],
        "description": article["seo_description"],
        "image": [image_url or str(request.url_for("static", path="images/brand/og-default.png"))],
        "author": author,
        "publisher": {"@type": "Organization", "name": settings.app_name, "logo": _logo(request)},
        "mainEntityOfPage": canonical_url,
        "articleSection": article.get("category", ""),
        "isAccessibleForFree": True,
    }
    if article.get("published_iso"):
        schema["datePublished"] = article["published_iso"]
    if article.get("updated_iso"):
        schema["dateModified"] = article["updated_iso"]
    if article.get("tags"):
        schema["keywords"] = ", ".join(article["tags"])
    return schema


def site_schema(request: Request) -> list[dict[str, Any]]:
    """Organization and WebSite (with the search box) for the homepage."""
    base = site_url(request)
    return [
        {"@context": "https://schema.org", "@type": "Organization", "name": settings.app_name,
         "url": f"{base}/", "logo": _logo(request), "slogan": TAGLINE},
        {"@context": "https://schema.org", "@type": "WebSite", "name": settings.app_name, "url": f"{base}/",
         "potentialAction": {"@type": "SearchAction", "target": f"{base}/search?q={{search_term_string}}",
                             "query-input": "required name=search_term_string"}},
    ]
