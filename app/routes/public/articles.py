from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates

from app.config.settings import settings
from app.services.article_page_service import get_article_listing_context


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/articles")
async def article_listing(
    request: Request,
    page: int = Query(default=1, ge=1),
    category: str | None = Query(default=None, max_length=120),
    tag: str | None = Query(default=None, max_length=64),
    sort: str = Query(default="newest", max_length=40),
):
    listing_context = await get_article_listing_context(
        page=page,
        category=category,
        tag=tag,
        sort=sort,
    )

    return templates.TemplateResponse(
        request,
        "pages/articles.html",
        {
            "app_name": settings.app_name,
            "page_title": "Articles",
            **listing_context,
        },
    )
