from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http_status
from fastapi.templating import Jinja2Templates
from pymongo.errors import PyMongoError

from app.config.settings import settings
from app.database.mongodb import get_database
from app.schemas.admin import AdminRead
from app.schemas.article import ArticleRead
from app.services.admin_dashboard_service import (
    get_admin_articles_context,
    get_admin_categories_context,
    get_admin_dashboard_context,
    get_admin_submissions_context,
)
from app.services.admin_session import get_current_admin
from app.services.article_service import ArticleService


router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


@router.get("")
async def admin_dashboard_page(
    request: Request,
    admin: AdminRead = Depends(get_current_admin),
):
    dashboard_context = await get_admin_dashboard_context()

    return _admin_template(
        request,
        "pages/admin_dashboard.html",
        admin=admin,
        active_nav="dashboard",
        page_title="Admin dashboard",
        context=dashboard_context.to_template_context(),
    )


@router.get("/articles")
async def admin_articles_page(
    request: Request,
    admin: AdminRead = Depends(get_current_admin),
):
    dashboard_context = await get_admin_articles_context()

    return _admin_template(
        request,
        "pages/admin_articles.html",
        admin=admin,
        active_nav="articles",
        page_title="Articles",
        context=dashboard_context.to_template_context(),
    )


@router.get("/articles/new")
async def admin_new_article_page(
    request: Request,
    admin: AdminRead = Depends(get_current_admin),
):
    dashboard_context = await get_admin_articles_context()

    return _admin_template(
        request,
        "pages/admin_article_editor.html",
        admin=admin,
        active_nav="articles",
        page_title="New article",
        context={
            **dashboard_context.to_template_context(),
            "article": None,
            "editor_mode": "create",
        },
    )


@router.get("/articles/{article_identifier}/edit")
async def admin_edit_article_page(
    request: Request,
    article_identifier: str,
    admin: AdminRead = Depends(get_current_admin),
):
    dashboard_context = await get_admin_articles_context()
    article = await _load_admin_article(article_identifier)
    if article is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Article was not found.",
        )

    return _admin_template(
        request,
        "pages/admin_article_editor.html",
        admin=admin,
        active_nav="articles",
        page_title=f"Edit {article.title}",
        context={
            **dashboard_context.to_template_context(),
            "article": article,
            "editor_mode": "update",
        },
    )


@router.get("/categories")
async def admin_categories_page(
    request: Request,
    admin: AdminRead = Depends(get_current_admin),
):
    dashboard_context = await get_admin_categories_context()

    return _admin_template(
        request,
        "pages/admin_categories.html",
        admin=admin,
        active_nav="categories",
        page_title="Categories",
        context=dashboard_context.to_template_context(),
    )


@router.get("/submissions")
async def admin_submissions_page(
    request: Request,
    admin: AdminRead = Depends(get_current_admin),
):
    dashboard_context = await get_admin_submissions_context()

    return _admin_template(
        request,
        "pages/admin_submissions.html",
        admin=admin,
        active_nav="submissions",
        page_title="Submissions",
        context=dashboard_context.to_template_context(),
    )


def _admin_template(
    request: Request,
    template_name: str,
    *,
    admin: AdminRead,
    active_nav: str,
    page_title: str,
    context: dict[str, Any],
):
    return templates.TemplateResponse(
        request,
        template_name,
        {
            "app_name": settings.app_name,
            "page_title": page_title,
            "seo_title": page_title,
            "seo_description": "Protected admin area for Infinity Den.",
            "robots": "noindex, nofollow",
            "use_admin_chrome": True,
            "admin": admin,
            "active_nav": active_nav,
            **context,
        },
    )


async def _load_admin_article(article_identifier: str) -> ArticleRead | None:
    try:
        db = get_database()
        return await ArticleService(database=db).get_article_detail(article_identifier)
    except (RuntimeError, PyMongoError):
        return None
