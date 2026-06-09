from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pymongo.errors import PyMongoError

from app.config.constants import (
    ARTICLE_STATUS_ARCHIVED,
    ARTICLE_STATUS_DRAFT,
    ARTICLE_STATUS_PUBLISHED,
    SUBMISSION_STATUS_ACCEPTED,
    SUBMISSION_STATUS_NEW,
    SUBMISSION_STATUS_REJECTED,
    SUBMISSION_STATUS_REVIEWING,
)
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.models.submission import ARTICLE_SUBMISSION_COLLECTION
from app.schemas.article import ArticleQueryParams, ArticleRead
from app.schemas.category import CategoryQueryParams, CategoryRead
from app.schemas.submission import ArticleSubmissionRead
from app.services.article_service import ArticleService
from app.services.category_service import CategoryService
from app.services.submission_service import SubmissionService


ADMIN_TABLE_LIMIT = 25
ADMIN_DASHBOARD_LIMIT = 6


@dataclass(frozen=True)
class AdminDashboardContext:
    is_database_available: bool
    stats: dict[str, int]
    status_counts: dict[str, int]
    submission_counts: dict[str, int]
    articles: list[ArticleRead]
    categories: list[CategoryRead]
    submissions: list[ArticleSubmissionRead]

    def to_template_context(self) -> dict[str, Any]:
        return {
            "is_database_available": self.is_database_available,
            "stats": self.stats,
            "status_counts": self.status_counts,
            "submission_counts": self.submission_counts,
            "articles": self.articles,
            "categories": self.categories,
            "submissions": self.submissions,
        }


async def get_admin_dashboard_context(
    *,
    article_limit: int = ADMIN_DASHBOARD_LIMIT,
    category_limit: int = ADMIN_DASHBOARD_LIMIT,
    submission_limit: int = ADMIN_DASHBOARD_LIMIT,
) -> AdminDashboardContext:
    try:
        db = get_database()
        articles = await ArticleService(database=db).list_articles(
            ArticleQueryParams(
                page=1,
                per_page=article_limit,
                sort_by="updated_at",
                sort_direction="desc",
            )
        )
        categories = await CategoryService(database=db).list_categories(
            CategoryQueryParams(
                page=1,
                per_page=category_limit,
                sort_by="name",
                sort_direction="asc",
            )
        )
        submissions = await SubmissionService(database=db).list_submissions(
            page=1,
            per_page=submission_limit,
        )

        status_counts = {
            ARTICLE_STATUS_DRAFT: await db[ARTICLE_COLLECTION].count_documents(
                {"status": ARTICLE_STATUS_DRAFT}
            ),
            ARTICLE_STATUS_PUBLISHED: await db[ARTICLE_COLLECTION].count_documents(
                {"status": ARTICLE_STATUS_PUBLISHED}
            ),
            ARTICLE_STATUS_ARCHIVED: await db[ARTICLE_COLLECTION].count_documents(
                {"status": ARTICLE_STATUS_ARCHIVED}
            ),
        }
        submission_counts = {
            SUBMISSION_STATUS_NEW: await db[
                ARTICLE_SUBMISSION_COLLECTION
            ].count_documents({"status": SUBMISSION_STATUS_NEW}),
            SUBMISSION_STATUS_REVIEWING: await db[
                ARTICLE_SUBMISSION_COLLECTION
            ].count_documents({"status": SUBMISSION_STATUS_REVIEWING}),
            SUBMISSION_STATUS_ACCEPTED: await db[
                ARTICLE_SUBMISSION_COLLECTION
            ].count_documents({"status": SUBMISSION_STATUS_ACCEPTED}),
            SUBMISSION_STATUS_REJECTED: await db[
                ARTICLE_SUBMISSION_COLLECTION
            ].count_documents({"status": SUBMISSION_STATUS_REJECTED}),
        }

        return AdminDashboardContext(
            is_database_available=True,
            stats={
                "articles": sum(status_counts.values()),
                "categories": await db[CATEGORY_COLLECTION].count_documents({}),
                "submissions": sum(submission_counts.values()),
                "featured": await db[ARTICLE_COLLECTION].count_documents(
                    {"is_featured": True}
                ),
            },
            status_counts=status_counts,
            submission_counts=submission_counts,
            articles=articles.items,
            categories=categories.items,
            submissions=submissions.items,
        )
    except (RuntimeError, PyMongoError):
        return _empty_admin_dashboard_context()


async def get_admin_articles_context() -> AdminDashboardContext:
    return await get_admin_dashboard_context(
        article_limit=ADMIN_TABLE_LIMIT,
        category_limit=100,
        submission_limit=ADMIN_DASHBOARD_LIMIT,
    )


async def get_admin_categories_context() -> AdminDashboardContext:
    return await get_admin_dashboard_context(
        article_limit=ADMIN_DASHBOARD_LIMIT,
        category_limit=ADMIN_TABLE_LIMIT,
        submission_limit=ADMIN_DASHBOARD_LIMIT,
    )


async def get_admin_submissions_context() -> AdminDashboardContext:
    return await get_admin_dashboard_context(
        article_limit=ADMIN_DASHBOARD_LIMIT,
        category_limit=ADMIN_DASHBOARD_LIMIT,
        submission_limit=ADMIN_TABLE_LIMIT,
    )


def _empty_admin_dashboard_context() -> AdminDashboardContext:
    return AdminDashboardContext(
        is_database_available=False,
        stats={
            "articles": 0,
            "categories": 0,
            "submissions": 0,
            "featured": 0,
        },
        status_counts={
            ARTICLE_STATUS_DRAFT: 0,
            ARTICLE_STATUS_PUBLISHED: 0,
            ARTICLE_STATUS_ARCHIVED: 0,
        },
        submission_counts={
            SUBMISSION_STATUS_NEW: 0,
            SUBMISSION_STATUS_REVIEWING: 0,
            SUBMISSION_STATUS_ACCEPTED: 0,
            SUBMISSION_STATUS_REJECTED: 0,
        },
        articles=[],
        categories=[],
        submissions=[],
    )
