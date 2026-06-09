from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config.settings import settings
from app.schemas.admin import AdminRead
from app.services.admin_session import get_optional_current_admin


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/login")
async def admin_login_page(
    request: Request,
    admin: AdminRead | None = Depends(get_optional_current_admin),
):
    if admin is not None:
        return RedirectResponse("/admin", status_code=303)

    return templates.TemplateResponse(
        request,
        "pages/admin_login.html",
        {
            "app_name": settings.app_name,
            "page_title": "Admin login",
            "seo_title": "Admin login",
            "seo_description": "Sign in to the Infinity Den admin area.",
            "robots": "noindex, nofollow",
        },
    )


@router.get("/admin")
async def admin_home_page(
    request: Request,
    admin: AdminRead | None = Depends(get_optional_current_admin),
):
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "pages/admin_home.html",
        {
            "app_name": settings.app_name,
            "page_title": "Admin",
            "seo_title": "Admin",
            "seo_description": "Protected admin area for Infinity Den.",
            "robots": "noindex, nofollow",
            "admin": admin,
        },
    )
