"""Sitemap, robots.txt, structured data, and inputs that try to smuggle in MongoDB operators."""

import asyncio
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.main import app
from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.models.debate import DEBATE_COLLECTION
from app.models.question import QUESTION_COLLECTION
from app.models.quiz import QUIZ_COLLECTION
from app.routes.public.seo import article_schema, robots_txt
from app.schemas.comment import CommentInput
from app.schemas.newsletter import NewsletterSubscriptionCreate
from app.schemas.report import ReportInput
from app.services.sitemap_service import sitemap_entries
from app.utils.forms import read_form
from tests.fakes import FakeCollection


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def _request(body: bytes = b"") -> Request:
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {"type": "http", "scheme": "https", "server": ("infinityden.test", 443), "path": "/",
             "query_string": b"", "headers": [], "app": app, "router": app.router, "root_path": ""}
    return Request(scope, receive)


def test_sitemap_lists_only_what_search_engines_should_see():
    database = {
        CATEGORY_COLLECTION: FakeCollection([{"name": "Cosmic Canvas", "subtitle": "Science", "slug": "science", "nav_order": 1}]),
        ARTICLE_COLLECTION: FakeCollection([
            {"slug": "live", "status": "published", "published_at": NOW, "updated_at": NOW},
            {"slug": "draft", "status": "draft", "published_at": None, "updated_at": NOW},
        ]),
        QUESTION_COLLECTION: FakeCollection([
            {"slug": "2026-01-01-past", "status": "published", "publish_date": "2026-01-01"},
            {"slug": "2999-01-01-future", "status": "published", "publish_date": "2999-01-01"},
            {"slug": "2026-01-02-draft", "status": "draft", "publish_date": "2026-01-02"},
        ]),
        QUIZ_COLLECTION: FakeCollection([{"slug": "claim-ab12", "status": "published", "updated_at": NOW},
                                         {"slug": "hidden-cd34", "status": "draft", "updated_at": NOW}]),
        DEBATE_COLLECTION: FakeCollection([{"slug": "remote-work-ab12", "status": "published", "updated_at": NOW},
                                           {"slug": "unset-cd34", "status": "draft", "updated_at": NOW}]),
    }
    paths = dict(asyncio.run(sitemap_entries(database)))
    assert {"/", "/categories/science", "/articles/live", "/questions/2026-01-01-past", "/play/claim-ab12",
            "/debates", "/debates/remote-work-ab12"} <= paths.keys()
    assert paths["/articles/live"] == "2026-10-16"
    assert not {"/articles/draft", "/questions/2999-01-01-future", "/questions/2026-01-02-draft", "/play/hidden-cd34",
                "/debates/unset-cd34"} & paths.keys()


def test_robots_keeps_private_pages_out_and_points_to_the_sitemap():
    text = asyncio.run(robots_txt(_request())).body.decode()
    for path in ("/admin", "/api/", "/account", "/saved", "/report"):
        assert f"Disallow: {path}" in text
    assert "Sitemap: https://infinityden.test/sitemap.xml" in text


def test_article_schema_names_the_member_author_and_publisher():
    article = {"title": "The Ship of Theseus", "seo_description": "A puzzle.", "author": "Mira", "author_url": "/members/mira",
               "category": "The Unanswered", "published_iso": "2026-10-11T08:00:00+00:00", "updated_iso": "", "tags": ["Identity"]}
    schema = article_schema(_request(), article, "https://infinityden.test/articles/theseus", "")
    assert schema["@type"] == "Article" and schema["author"]["url"] == "https://infinityden.test/members/mira"
    assert schema["image"][0].endswith("/static/images/brand/og-default.png")
    assert schema["publisher"]["name"] == "Infinity Den" and "dateModified" not in schema


# --- NoSQL injection: operators never reach a query -----------------------------

def test_form_fields_are_always_plain_strings():
    form = asyncio.run(read_form(_request(b"email[$ne]=&body=%7B%22%24gt%22%3A%22%22%7D")))
    # Brackets stay part of the field name, and JSON stays text: no nested objects.
    assert form == {"email[$ne]": "", "body": '{"$gt":""}'}


@pytest.mark.parametrize(
    "build",
    [
        lambda: NewsletterSubscriptionCreate(email={"$ne": ""}),
        lambda: CommentInput(body={"$gt": ""}),
        lambda: ReportInput(target_type="comment", target_id={"$ne": None}, reason="spam"),
        lambda: ReportInput(target_type={"$in": ["comment"]}, target_id="a" * 24, reason="spam"),
    ],
)
def test_operator_shaped_json_is_rejected(build):
    with pytest.raises(ValidationError):
        build()
