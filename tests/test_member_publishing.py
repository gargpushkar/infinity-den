"""Member publishing: safe markdown, ownership, review flow.

No database: MemberArticleService runs against a small in-memory stand-in.
"""

import asyncio
import json
import shutil
import subprocess
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pytest

from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.schemas.article import MemberPieceInput
from app.schemas.user import MemberRead
from app.services.member_article_service import (
    MemberArticleService,
    PieceInvalidError,
    PieceLockedError,
    PieceNotFoundError,
    parse_sources,
    piece_slug,
)
from app.utils.markdown import render_markdown
from tests.fakes import FakeCollection


# --- safe markdown -------------------------------------------------------------

ATTACKS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    '[click](javascript:alert(1))',
    '[click](https://example.org"onmouseover="alert(1))',
    "## <b>heading</b>",
    "- <iframe src=https://evil.example></iframe>",
    "> <svg onload=alert(1)>",
]


class _TagCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def _tags(html: str) -> list[tuple[str, dict[str, str | None]]]:
    collector = _TagCollector()
    collector.feed(html)
    return collector.tags


@pytest.mark.parametrize("attack", ATTACKS)
def test_markdown_never_emits_dangerous_markup(attack):
    for tag, attrs in _tags(str(render_markdown(attack))):
        assert tag in {"p", "h2", "h3", "ul", "li", "blockquote", "strong", "em", "code", "a"}
        if tag == "a":
            assert set(attrs) == {"href", "target", "rel"}
            assert attrs["href"].startswith(("http://", "https://"))
        else:
            assert attrs == {}


def test_markdown_formats_the_supported_subset():
    html = str(render_markdown("## Title\n\nSome **bold** and _soft_ `code`.\n- one\n- two\n> quoted"))
    assert "<h2>Title</h2>" in html
    assert "<strong>bold</strong>" in html and "<em>soft</em>" in html and "<code>code</code>" in html
    assert "<ul><li>one</li><li>two</li></ul>" in html
    assert "<blockquote>quoted</blockquote>" in html


def test_markdown_link_with_underscores_stays_intact():
    html = str(render_markdown("See [the _model_](https://en.wikipedia.org/wiki/Large_language_model)."))
    assert 'href="https://en.wikipedia.org/wiki/Large_language_model"' in html
    assert "<em>model</em>" in html  # formatting still works inside the link text


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_editor_preview_matches_published_page():
    """The JS preview in main.js and the Python renderer must agree."""
    source = Path("app/static/js/main.js").read_text()
    start = source.index("  const escapeHtml = (value) =>")
    end = source.index("  const insertMarkdown = (textarea, action) =>")
    samples = [
        *ATTACKS,
        "## Heading\nPlain line with **bold**, _italic_ and `code`.\n- a [link](https://example.org/a_b_c)\n- two\n\n> quote",
        "Tom's \"quoted\" & <angled> text",
    ]
    script = source[start:end] + "\nprocess.stdout.write(JSON.stringify(%s.map(renderMarkdownPreview)));" % json.dumps(samples)
    js_output = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)

    for sample, js_html in zip(samples, js_output):
        python_html = str(render_markdown(sample)).replace("&#x27;", "&#39;")
        assert python_html == js_html, sample


# --- member pieces ---------------------------------------------------------------

NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def _member(member_id: str = "0123456789abcdef01234567") -> MemberRead:
    return MemberRead(_id=member_id, username="mira", display_name="Mira", email="m@example.org", created_at=NOW)


def _input(**overrides) -> MemberPieceInput:
    data = {
        "title": "What failure taught me",
        "excerpt": "A short summary of the piece.",
        "content": "Body text.",
        "category_id": "personal-stories",
        "article_format": "experience",
        **overrides,
    }
    return MemberPieceInput(**data)


def _service(*articles) -> MemberArticleService:
    database = {
        ARTICLE_COLLECTION: FakeCollection(articles),
        CATEGORY_COLLECTION: FakeCollection([{"slug": "personal-stories"}, {"slug": "science"}]),
    }
    return MemberArticleService(database=database)


def _stored(service: MemberArticleService) -> list[dict]:
    return service.database[ARTICLE_COLLECTION].documents


def test_save_draft_and_submit_never_publish():
    service = _service()
    draft = asyncio.run(service.save(_member(), _input(), submit=False))
    assert draft.status == "draft"
    assert draft.author_id == _member().id and draft.author == "Mira"

    submitted = asyncio.run(service.save(_member(), _input(), submit=True, article_id=draft.id))
    assert submitted.status == "pending_review"
    assert all(d["status"] != "published" for d in _stored(service))


def test_members_cannot_touch_each_others_pieces():
    service = _service()
    piece = asyncio.run(service.save(_member(), _input(), submit=False))
    stranger = _member("fedcba9876543210fedcba98")
    with pytest.raises(PieceNotFoundError):
        asyncio.run(service.get_own(stranger, piece.id))
    with pytest.raises(PieceNotFoundError):
        asyncio.run(service.save(stranger, _input(title="Hijacked title"), submit=True, article_id=piece.id))
    assert _stored(service)[0]["title"] == "What failure taught me"


def test_published_piece_is_locked_for_its_author():
    service = _service()
    piece = asyncio.run(service.save(_member(), _input(), submit=True))
    _stored(service)[0]["status"] = "published"
    with pytest.raises(PieceLockedError):
        asyncio.run(service.save(_member(), _input(title="Quietly changed"), submit=False, article_id=piece.id))


def test_researched_submission_needs_sources_but_draft_does_not():
    service = _service()
    asyncio.run(service.save(_member(), _input(article_format="article"), submit=False))
    with pytest.raises(PieceInvalidError) as error:
        asyncio.run(service.save(_member(), _input(article_format="article"), submit=True))
    assert error.value.field == "sources"


def test_unknown_room_is_rejected():
    with pytest.raises(PieceInvalidError) as error:
        asyncio.run(_service().save(_member(), _input(category_id="business"), submit=False))
    assert error.value.field == "category_id"


def test_resubmitting_clears_the_editors_note():
    service = _service()
    piece = asyncio.run(service.save(_member(), _input(), submit=True))
    _stored(service)[0].update({"status": "draft", "review_note": "Add an example."})
    resubmitted = asyncio.run(service.save(_member(), _input(), submit=True, article_id=piece.id))
    assert resubmitted.status == "pending_review"
    assert resubmitted.review_note is None


# --- small helpers ---------------------------------------------------------------

def test_piece_slug_is_readable_and_unique():
    first, second = piece_slug("What failure taught me!"), piece_slug("What failure taught me!")
    assert first.startswith("what-failure-taught-me-") and first != second


def test_parse_sources_matches_the_admin_editor_format():
    assert parse_sources("Paper | https://a.org\nhttps://b.org\n\n") == [
        {"title": "Paper", "url": "https://a.org"},
        {"title": "https://b.org", "url": "https://b.org"},
    ]
