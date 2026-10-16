from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http_status
from fastapi.templating import Jinja2Templates
from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_STATUS_PENDING_REVIEW
from app.config.settings import settings
from app.database.mongodb import get_database
from app.schemas.admin import AdminRead
from app.schemas.article import ArticleQueryParams, ArticleRead
from app.services.admin_dashboard_service import (
    get_admin_articles_context,
    get_admin_categories_context,
    get_admin_dashboard_context,
    get_admin_submissions_context,
)
from app.services.admin_auth_service import AdminAuthService
from app.services.admin_csrf import ADMIN_CSRF_COOKIE, issue_admin_csrf_token
from app.services.admin_permissions import require_admin_manager
from app.services.admin_session import get_current_admin
from app.services.article_service import ArticleService
from app.services.nav_service import get_rooms
from app.services.question_service import QuestionService, site_today
from app.services.user_service import UserService


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
        context={
            **dashboard_context.to_template_context(),
            "review_queue": await _load_review_queue(),
        },
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
            "submitted_by": await _load_member(article.author_id),
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


@router.get("/questions")
async def admin_questions_page(
    request: Request,
    admin: AdminRead = Depends(get_current_admin),
):
    try:
        db = get_database()
        questions = await QuestionService(database=db).list_questions()
        counts = await QuestionService(database=db).response_counts([q.id for q in questions])
        rooms = await get_rooms(db)
    except (RuntimeError, PyMongoError):
        questions, counts, rooms = [], {}, []

    return _admin_template(
        request,
        "pages/admin_questions.html",
        admin=admin,
        active_nav="questions",
        page_title="Question Room",
        context={"questions": questions, "response_counts": counts, "rooms": rooms, "today": site_today()},
    )


@router.get("/questions/{question_id}")
async def admin_question_page(
    request: Request,
    question_id: str,
    admin: AdminRead = Depends(get_current_admin),
):
    try:
        db = get_database()
        service = QuestionService(database=db)
        question = await service.get_question(question_id)
        responses = await service.all_responses(question_id) if question else []
        rooms = await get_rooms(db)
    except (RuntimeError, PyMongoError):
        question, responses, rooms = None, [], []
    if question is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Question was not found.")

    return _admin_template(
        request,
        "pages/admin_question_detail.html",
        admin=admin,
        active_nav="questions",
        page_title="Question Room",
        context={"question": question, "responses": responses, "rooms": rooms, "today": site_today()},
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


@router.get("/users")
async def admin_users_page(
    request: Request,
    admin: AdminRead = Depends(require_admin_manager),
):
    context = await _load_admin_users_context()

    return _admin_template(
        request,
        "pages/admin_users.html",
        admin=admin,
        active_nav="users",
        page_title="Admin users",
        context=context,
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
    csrf_token = issue_admin_csrf_token()
    response = templates.TemplateResponse(
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
            "csrf_token": csrf_token,
            "active_nav": active_nav,
            **context,
        },
    )
    response.set_cookie(
        ADMIN_CSRF_COOKIE,
        csrf_token,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )

    return response


async def _load_admin_article(article_identifier: str) -> ArticleRead | None:
    try:
        db = get_database()
        return await ArticleService(database=db).get_article_detail(article_identifier)
    except (RuntimeError, PyMongoError):
        return None


async def _load_review_queue() -> list[ArticleRead]:
    """Member pieces waiting for an editor, oldest first."""
    try:
        listing = await ArticleService(database=get_database()).list_articles(
            ArticleQueryParams(
                per_page=100,
                status=ARTICLE_STATUS_PENDING_REVIEW,
                sort_by="updated_at",
                sort_direction="asc",
            )
        )
        return listing.items
    except (RuntimeError, PyMongoError):
        return []


async def _load_member(member_id: str | None) -> Any:
    if not member_id:
        return None
    try:
        return await UserService(database=get_database()).get_member_by_id(member_id)
    except (RuntimeError, PyMongoError):
        return None


async def _load_admin_users_context() -> dict[str, Any]:
    try:
        db = get_database()
        admin_users = await AdminAuthService(database=db).list_admins()
        return {
            "is_database_available": True,
            "admin_users": admin_users.items,
            "admin_user_stats": {
                "total": admin_users.total,
                "active_admins": admin_users.active_admins,
                "active_editors": admin_users.active_editors,
            },
        }
    except (RuntimeError, PyMongoError):
        return {
            "is_database_available": False,
            "admin_users": [],
            "admin_user_stats": {
                "total": 0,
                "active_admins": 0,
                "active_editors": 0,
            },
        }
