from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config.settings import settings
from app.services.home_service import get_homepage_context
from app.services.nav_service import get_nav_context


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def homepage(request: Request):
    nav_context = await get_nav_context(request)
    homepage_context = await get_homepage_context()

    return templates.TemplateResponse(
        request,
        "pages/home.html",
        {
            **nav_context,
            "app_name": settings.app_name,
            "page_title": "A universe of ideas",
            **homepage_context,
        },
    )
