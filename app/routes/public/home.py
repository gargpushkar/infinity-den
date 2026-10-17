import asyncio

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from app.config.settings import settings
from app.routes.public.seo import site_schema
from app.services.home_service import get_homepage_context
from app.services.nav_service import get_nav_context


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def homepage(
    request: Request,
    claim: str | None = Query(default=None, max_length=120),
    answer: str = Query(default="", max_length=10),
    after: str | None = Query(default=None, max_length=120),
):
    """`?claim=…&answer=…` answers the Fact or Fiction card in place."""
    nav_context, context = await asyncio.gather(
        get_nav_context(request),
        get_homepage_context(claim_slug=claim, answer=answer, after=after),
    )
    is_answered = bool(context["arcade"] and context["arcade"]["is_answered"])

    return templates.TemplateResponse(
        request,
        "pages/home.html",
        {
            **nav_context,
            **context,
            "app_name": settings.app_name,
            "page_title": "A universe of ideas",
            # One homepage: answered views point back to it and stay out of search.
            "canonical_url": str(request.url_for("homepage")),
            "robots": "noindex, follow" if is_answered else "index, follow",
            "page_schema": site_schema(request),
        },
    )


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    # Browsers request /favicon.ico on every page, whatever the <link> tags say.
    return FileResponse(
        "app/static/icons/favicon.ico",
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=604800"},
    )
