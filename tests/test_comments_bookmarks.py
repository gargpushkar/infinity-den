"""Comments and bookmarks: safe rendering, ownership, hidden comments, saved list."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.models.article import ARTICLE_COLLECTION
from app.models.bookmark import BOOKMARK_COLLECTION
from app.models.comment import COMMENT_COLLECTION
from app.schemas.comment import CommentInput, CommentRead
from app.schemas.user import MemberRead
from app.services.article_conversation_service import comment_view, get_conversation_context, published_article_id
from app.services.bookmark_service import BookmarkService
from app.services.comment_service import CommentService
from tests.fakes import FakeCollection


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)
MIRA = MemberRead(_id="0123456789abcdef01234567", username="mira", display_name="Mira", email="m@x.org", created_at=NOW)
SAM = MemberRead(_id="fedcba9876543210fedcba98", username="sam", display_name="Sam", email="s@x.org", created_at=NOW)
ARTICLE_ID = "aaaaaaaaaaaaaaaaaaaaaaaa"


def _run(coroutine):
    return asyncio.run(coroutine)


def _comment(body: str, member: MemberRead, *, status: str = "published", minutes: int = 0) -> dict:
    return {"article_id": ARTICLE_ID, "user_id": member.id, "author": member.display_name,
            "author_username": member.username, "body": body, "status": status,
            "created_at": NOW + timedelta(minutes=minutes), "updated_at": NOW}


def _piece(object_id: str, slug: str, status: str = "published") -> dict:
    return {"_id": ObjectId(object_id), "title": f"Piece {slug}", "slug": slug, "excerpt": "An excerpt long enough.",
            "content": "Body", "author": "Writer", "status": status, "created_at": NOW, "updated_at": NOW}


def _database(comments=(), articles=(), bookmarks=()) -> dict:
    return {
        COMMENT_COLLECTION: FakeCollection(comments),
        ARTICLE_COLLECTION: FakeCollection(articles),
        BOOKMARK_COLLECTION: FakeCollection(bookmarks, unique=("user_id", "article_id")),
    }


# --- comments ----------------------------------------------------------------

@pytest.mark.parametrize("attack", ["<script>alert(1)</script>", "[x](javascript:alert(1))", "<img src=x onerror=alert(1)>"])
def test_comment_html_is_never_rendered(attack):
    comment = CommentRead.model_validate({**_comment(attack, MIRA), "_id": ObjectId()})
    html = str(comment_view(comment, MIRA)["body_html"])
    assert "<script" not in html and "<img" not in html and 'href="javascript' not in html


def test_comment_length_limits():
    CommentInput(body="x" * 2000)
    for body in ("x" * 2001, "   ", "x"):
        with pytest.raises(ValidationError):
            CommentInput(body=body)


def test_hidden_comments_are_visible_only_to_their_author():
    database = _database([
        _comment("Second.", SAM, minutes=2),
        _comment("First.", MIRA, minutes=1),
        _comment("Mira's hidden one.", MIRA, status="hidden", minutes=3),
        _comment("Sam's hidden one.", SAM, status="hidden", minutes=4),
    ])
    as_mira = _run(get_conversation_context(ARTICLE_ID, MIRA, database=database))
    assert [c["author"] for c in as_mira["comments"]] == ["Mira", "Sam", "Mira"]  # oldest first
    assert as_mira["comments"][-1]["is_hidden"] and as_mira["comment_count"] == 2
    as_visitor = _run(get_conversation_context(ARTICLE_ID, None, database=database))
    assert len(as_visitor["comments"]) == 2 and not any(c["is_own"] for c in as_visitor["comments"])


def test_members_only_delete_their_own_comments():
    service = CommentService(database=_database())
    mine = _run(service.add(ARTICLE_ID, MIRA, CommentInput(body="Mine to delete.")))
    assert _run(service.delete_own(mine.id, SAM)) is False
    assert _run(service.delete_own("not-an-id", MIRA)) is False
    assert _run(service.delete_own(mine.id, MIRA)) is True


# --- bookmarks ---------------------------------------------------------------

def test_saving_twice_keeps_one_bookmark_and_remove_clears_it():
    service = BookmarkService(database=_database())
    _run(service.save(MIRA, ARTICLE_ID))
    _run(service.save(MIRA, ARTICLE_ID))
    assert len(service.bookmarks.documents) == 1 and _run(service.is_saved(MIRA, ARTICLE_ID))
    assert not _run(service.is_saved(SAM, ARTICLE_ID))
    _run(service.remove(MIRA, ARTICLE_ID))
    assert not _run(service.is_saved(MIRA, ARTICLE_ID))


def test_saved_list_is_newest_first_and_drops_unpublished_pieces():
    first, second, gone = "1" * 24, "2" * 24, "3" * 24
    database = _database(
        articles=[_piece(first, "first"), _piece(second, "second"), _piece(gone, "gone", status="archived")],
        bookmarks=[
            {"user_id": MIRA.id, "article_id": first, "created_at": NOW},
            {"user_id": MIRA.id, "article_id": second, "created_at": NOW + timedelta(hours=1)},
            {"user_id": MIRA.id, "article_id": gone, "created_at": NOW + timedelta(hours=2)},
            {"user_id": SAM.id, "article_id": first, "created_at": NOW},
        ],
    )
    saved = _run(BookmarkService(database=database).saved_articles(MIRA))
    assert [article.slug for article in saved] == ["second", "first"]


def test_only_published_pieces_take_comments_or_bookmarks():
    database = _database(articles=[_piece("1" * 24, "live"), _piece("2" * 24, "draft", status="draft")])
    assert _run(published_article_id("live", database=database)) == "1" * 24
    assert _run(published_article_id("draft", database=database)) is None
