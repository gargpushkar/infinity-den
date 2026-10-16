"""Fact or Fiction: answers, no spoilers, drafts hidden, links checked."""

import asyncio
from datetime import datetime, timezone

import pytest

from app.models.article import ARTICLE_COLLECTION
from app.models.quiz import QUIZ_COLLECTION
from app.schemas.quiz import QuizItemInput, QuizItemRead
from app.services.play_page_service import claim_context
from app.services.quiz_service import QuizArticleNotFoundError, QuizService, is_correct
from tests.fakes import FakeCollection


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def _claim(slug: str, *, is_true: bool = False, status: str = "published", **extra) -> dict:
    return {
        "claim": f"Claim {slug} is worth checking.",
        "slug": slug,
        "is_true": is_true,
        "explanation": "Because <script>alert(1)</script> and **reasons**.",
        "article_slug": None,
        "category_id": None,
        "status": status,
        "created_at": NOW,
        "updated_at": NOW,
        **extra,
    }


def _service(claims=(), articles=()) -> QuizService:
    return QuizService(database={QUIZ_COLLECTION: FakeCollection(claims), ARTICLE_COLLECTION: FakeCollection(articles)})


def _run(coroutine):
    return asyncio.run(coroutine)


@pytest.mark.parametrize(
    ("is_true", "answer", "expected"),
    [(True, "fact", True), (True, "fiction", False), (False, "fiction", True), (False, "fact", False), (True, "", None), (True, "maybe", None)],
)
def test_is_correct(is_true, answer, expected):
    item = QuizItemRead.model_validate({**_claim("a"), "_id": "x", "is_true": is_true})
    assert is_correct(item, answer) is expected


def test_drafts_are_never_played():
    service = _service([_claim("live"), _claim("draft", status="draft")])
    assert _run(service.get_published("draft")) is None
    assert all(_run(service.random_published()).slug == "live" for _ in range(20))


def test_next_claim_avoids_the_one_just_played():
    service = _service([_claim("one"), _claim("two")])
    assert all(_run(service.random_published(exclude_slug="one")).slug == "two" for _ in range(20))
    # With only one claim, replaying it beats showing nothing.
    assert _run(_service([_claim("only")]).random_published(exclude_slug="only")).slug == "only"


def test_no_spoilers_before_answering():
    service = _service([_claim("myth", is_true=False)])
    item = _run(service.get_published("myth"))
    unanswered = _run(claim_context(service, item, answer=""))["claim"]
    assert unanswered["is_answered"] is False
    assert not {"is_correct", "truth_label", "explanation_html"} & unanswered.keys()


def test_answer_reveals_truth_with_safe_explanation():
    service = _service([_claim("myth", is_true=False)])
    item = _run(service.get_published("myth"))
    revealed = _run(claim_context(service, item, answer="fiction"))["claim"]
    assert revealed["is_correct"] is True and revealed["truth_label"] == "Fiction"
    html = str(revealed["explanation_html"])
    assert "<script>" not in html and "&lt;script&gt;" in html and "<strong>reasons</strong>" in html


def test_only_published_articles_can_be_linked():
    articles = [
        {"slug": "live-article", "title": "Live", "status": "published"},
        {"slug": "draft-article", "title": "Draft", "status": "draft"},
    ]
    service = _service(articles=articles)
    base = {"claim": "A claim long enough.", "is_true": True, "explanation": "An explanation long enough."}
    _run(service.create_item(QuizItemInput(**base, article_slug="live-article")))
    _run(service.create_item(QuizItemInput(**base)))  # no article is fine
    for slug in ("draft-article", "missing-article"):
        with pytest.raises(QuizArticleNotFoundError):
            _run(service.create_item(QuizItemInput(**base, article_slug=slug)))


def test_linked_article_disappears_if_it_is_unpublished():
    service = _service(
        [_claim("c", article_slug="gone")],
        [{"slug": "gone", "title": "Gone", "status": "archived"}],
    )
    item = _run(service.get_published("c"))
    assert _run(service.linked_article(item)) is None
