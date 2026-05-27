from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config.settings import settings
from app.services.home_service import get_homepage_context


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def homepage(request: Request):
    homepage_context = await get_homepage_context()

    return templates.TemplateResponse(
        request,
        "pages/home.html",
        {
            "app_name": settings.app_name,
            "page_title": "Content publishing that stays organized",
            **homepage_context,
        },
    )
