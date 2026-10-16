from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates

from app.config.settings import settings
from app.services.experiences_page_service import get_experiences_context
from app.services.nav_service import get_nav_context


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/experiences")
async def human_library(
    request: Request,
    page: int = Query(default=1, ge=1),
    room: str | None = Query(default=None, max_length=120),
):
    return templates.TemplateResponse(
        request,
        "pages/experiences.html",
        {
            **await get_nav_context(request),
            **await get_experiences_context(page=page, room=room),
            "app_name": settings.app_name,
            "page_title": "The Human Library",
            "seo_title": "The Human Library",
            "seo_description": "Real experiences. Honest reflections. Different lives. Personal accounts from the Infinity Den community.",
        },
    )
