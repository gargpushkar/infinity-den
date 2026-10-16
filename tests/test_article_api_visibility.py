"""Unpublished articles must stay out of the public article API.

The route functions are called directly with a fake service, so these checks
need neither MongoDB nor an HTTP client.
"""

import asyncio
import inspect
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from pydantic.fields import FieldInfo

from app.routes.api import articles as articles_api
from app.schemas.admin import AdminRead
from app.schemas.article import ArticleListResponse, ArticleRead


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)
ADMIN = AdminRead(_id="admin-1", username="editor", role="editor")


def _article(slug: str, status: str) -> ArticleRead:
    return ArticleRead(
        _id=slug,
        title=f"Article {slug}",
        slug=slug,
        excerpt="An excerpt long enough to validate.",
        content="Body",
        author="Writer",
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


class FakeArticleService:
    def __init__(self) -> None:
        self.articles = [_article("live-piece", "published"), _article("secret-draft", "draft")]

    async def list_articles(self, query):
        items = [a for a in self.articles if query.status is None or a.status == query.status]
        return ArticleListResponse(
            items=items,
            total=len(items),
            page=query.page,
            per_page=query.per_page,
            total_pages=1,
            sort_by=query.sort_by,
            sort_direction=query.sort_direction,
        )

    async def get_article_detail(self, identifier):
        return next((a for a in self.articles if a.slug == identifier), None)


def _call(route, **overrides):
    """Call a FastAPI route function, filling Query() parameters with their defaults."""
    kwargs = {
        name: param.default.default
        for name, param in inspect.signature(route).parameters.items()
        if isinstance(param.default, FieldInfo)
    }
    kwargs.update(overrides)
    return asyncio.run(route(**kwargs))


def _listed_slugs(admin, status=None):
    response = _call(
        articles_api.list_articles,
        article_status=status,
        admin=admin,
        article_service=FakeArticleService(),
    )
    return [article.slug for article in response.items]


def test_anonymous_list_shows_only_published():
    assert _listed_slugs(admin=None) == ["live-piece"]


def test_anonymous_cannot_request_drafts_by_status():
    assert _listed_slugs(admin=None, status="draft") == ["live-piece"]


def test_admin_list_sees_drafts():
    assert _listed_slugs(admin=ADMIN) == ["live-piece", "secret-draft"]
    assert _listed_slugs(admin=ADMIN, status="draft") == ["secret-draft"]


def test_anonymous_draft_detail_is_not_found():
    with pytest.raises(HTTPException) as error:
        _call(
            articles_api.get_article_detail,
            article_identifier="secret-draft",
            admin=None,
            article_service=FakeArticleService(),
        )
    assert error.value.status_code == 404


def test_detail_visibility():
    published = _call(
        articles_api.get_article_detail,
        article_identifier="live-piece",
        admin=None,
        article_service=FakeArticleService(),
    )
    draft = _call(
        articles_api.get_article_detail,
        article_identifier="secret-draft",
        admin=ADMIN,
        article_service=FakeArticleService(),
    )
    assert published.slug == "live-piece"
    assert draft.slug == "secret-draft"
