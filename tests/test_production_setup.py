"""Fresh-database setup: launch rooms are created once, and tags appear when pieces are published."""

import asyncio
from datetime import datetime, timezone

from app.config.constants import LAUNCH_ROOMS
from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.models.tag import TAG_COLLECTION
from app.schemas.article import ArticleCreate, ArticleUpdate
from app.services.article_service import ArticleService
from app.services.tag_service import tag_slug
from scripts.create_launch_rooms import create_missing_rooms
from tests.fakes import FakeCollection


def _run(coroutine):
    return asyncio.run(coroutine)


def test_launch_rooms_are_created_once_and_edits_are_kept():
    renamed = {"name": "Starfield", "slug": "science", "subtitle": "Edited by an editor"}
    db = {CATEGORY_COLLECTION: FakeCollection([renamed])}
    created = _run(create_missing_rooms(db))
    assert sorted(created) == sorted(str(room["slug"]) for room in LAUNCH_ROOMS if room["slug"] != "science")
    assert _run(create_missing_rooms(db)) == []  # running it again changes nothing
    assert db[CATEGORY_COLLECTION].documents[0]["name"] == "Starfield"
    assert len(db[CATEGORY_COLLECTION].documents) == len(LAUNCH_ROOMS)


def _piece(**fields) -> ArticleCreate:
    return ArticleCreate(**{"title": "A piece about time", "slug": "a-piece-about-time", "excerpt": "An excerpt long enough.",
                            "content": "Body", "author": "Editor", "category_id": "history", "article_format": "experience",
                            "tags": ["Memory", "Deep time"], **fields})


def test_tags_are_registered_only_when_a_piece_is_published():
    db = {ARTICLE_COLLECTION: FakeCollection(), TAG_COLLECTION: FakeCollection([{"name": "Memory", "slug": "memory"}])}
    service = ArticleService(database=db)
    draft = _run(service.create_article(_piece(status="draft")))
    assert [t["slug"] for t in db[TAG_COLLECTION].documents] == ["memory"]  # drafts add nothing

    _run(service.update_article(draft.id, ArticleUpdate(status="published", published_at=datetime.now(timezone.utc))))
    assert sorted(t["slug"] for t in db[TAG_COLLECTION].documents) == ["deep-time", "memory"]  # no duplicate "memory"


def test_tag_slugs_match_the_seeded_ones():
    assert tag_slug("Thought experiments") == "thought-experiments"
    assert tag_slug("Self-knowledge") == "self-knowledge"
    assert tag_slug("  AI  ") == "ai"
