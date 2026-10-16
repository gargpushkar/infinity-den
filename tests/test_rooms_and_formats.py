"""Rooms, contribution formats, and the sources rule.

No database: the service is given an in-memory stand-in for its collection.
"""

import asyncio
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.article import ARTICLE_COLLECTION, missing_required_sources
from app.schemas.article import ArticleRead, ArticleSource, ArticleUpdate
from app.services.article_page_service import article_to_card_context
from app.services.article_service import ArticleService, ArticleSourcesRequiredError
from app.services.category_page_service import _format_filters, _room_page_url


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)
ARTICLE_ID = "0123456789abcdef01234567"


def _article(**overrides) -> ArticleRead:
    data = {
        "_id": "a1",
        "title": "A sample piece",
        "slug": "a-sample-piece",
        "excerpt": "An excerpt long enough to validate.",
        "content": "Body",
        "author": "Sample writer",
        "category_id": "science",
        "created_at": NOW,
        "updated_at": NOW,
        **overrides,
    }
    return ArticleRead(**data)


# --- the rule itself ---------------------------------------------------------

@pytest.mark.parametrize(
    ("article_format", "status", "sources", "blocked"),
    [
        ("article", "published", [], True),
        ("article", "published", [{"title": "x", "url": "https://x.org"}], False),
        ("article", "draft", [], False),
        ("experience", "published", [], False),
        ("perspective", "published", [], False),
    ],
)
def test_missing_required_sources(article_format, status, sources, blocked):
    assert missing_required_sources(
        article_format=article_format, status=status, sources=sources
    ) is blocked


# --- the rule through the service, including partial updates ----------------

class FakeCollection:
    def __init__(self, document):
        self.document = document
        self.updated = False

    async def find_one(self, *_args, **_kwargs):
        return dict(self.document)

    async def find_one_and_update(self, _filter, update, **_kwargs):
        self.updated = True
        self.document.update(update["$set"])
        return {
            "_id": ARTICLE_ID,
            "title": "A sample piece",
            "slug": "a-sample-piece",
            "excerpt": "An excerpt long enough to validate.",
            "content": "Body",
            "author": "Sample writer",
            "created_at": NOW,
            "updated_at": NOW,
            **self.document,
        }


def _service(document) -> tuple[ArticleService, FakeCollection]:
    collection = FakeCollection(document)
    return ArticleService(database={ARTICLE_COLLECTION: collection}), collection


def test_publish_action_cannot_bypass_sources():
    # The admin "publish" button sends only the status.
    service, collection = _service({"article_format": "article", "status": "draft", "sources": []})
    with pytest.raises(ArticleSourcesRequiredError):
        asyncio.run(service.update_article(ARTICLE_ID, ArticleUpdate(status="published")))
    assert collection.updated is False


def test_publish_with_sources_succeeds():
    service, collection = _service(
        {"article_format": "article", "status": "draft", "sources": [{"title": "x", "url": "https://x.org"}]}
    )
    article = asyncio.run(service.update_article(ARTICLE_ID, ArticleUpdate(status="published")))
    assert article.status == "published"
    assert collection.updated is True


def test_unrelated_update_is_never_blocked():
    # Featuring an older sourceless article must still work.
    service, collection = _service({"article_format": "article", "status": "published", "sources": []})
    asyncio.run(service.update_article(ARTICLE_ID, ArticleUpdate(is_featured=True)))
    assert collection.updated is True


# --- what readers see -------------------------------------------------------

def test_card_links_to_canonical_room_and_shows_labels():
    card = article_to_card_context(
        _article(article_format="article", is_speculative=True),
        {"science": "Cosmic Canvas"},
    )
    assert card["category_url"] == "/categories/science"
    assert card["category"] == "Cosmic Canvas"
    assert card["format_label"] == "Researched"
    assert card["speculative_label"] == "Speculation"


@pytest.mark.parametrize(
    ("article_format", "label"),
    [("experience", "Personal experience"), ("perspective", "Opinion")],
)
def test_format_labels(article_format, label):
    card = article_to_card_context(_article(article_format=article_format), {})
    assert card["format_label"] == label
    assert card["speculative_label"] == ""


def test_room_urls():
    assert _room_page_url("science", None) == "/categories/science"
    assert _room_page_url("science", "experience") == "/categories/science?format=experience"
    assert _room_page_url("science", None, page="{page}") == "/categories/science?page={page}"
    filters = _format_filters("science", "opinion-is-not-a-format")
    assert [f["label"] for f in filters] == ["All", "Researched", "Personal experience", "Opinion"]


# --- source validation ------------------------------------------------------

def test_source_title_defaults_to_url():
    assert ArticleSource(url="https://example.org/a").title == "https://example.org/a"


@pytest.mark.parametrize("url", ["javascript:alert(1)", "example.org", "ftp://example.org"])
def test_source_rejects_non_http_urls(url):
    with pytest.raises(ValidationError):
        ArticleSource(title="Bad", url=url)
