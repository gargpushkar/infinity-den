"""The homepage: sections in vision order, no repeats, drafts hidden, Arcade answered in place."""

import asyncio
from datetime import datetime, timedelta, timezone

from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.models.question import QUESTION_COLLECTION, RESPONSE_COLLECTION
from app.models.quiz import QUIZ_COLLECTION
from app.services.home_service import get_homepage_context
from app.services.question_service import site_today
from tests.fakes import FakeCollection


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def _piece(slug: str, *, days_ago: int = 1, **fields) -> dict:
    return {
        "title": f"Piece {slug}", "slug": slug, "excerpt": "An excerpt long enough to validate.",
        "content": "Body", "author": "Writer", "status": "published", "category_id": "science",
        "article_format": "article", "is_featured": False, "is_editors_pick": False, "author_id": None,
        "published_at": NOW - timedelta(days=days_ago), "created_at": NOW, "updated_at": NOW, **fields,
    }


def _claim(slug: str, status: str = "published") -> dict:
    return {"claim": f"Claim {slug} is surprising.", "slug": slug, "is_true": False, "status": status,
            "explanation": "Because of **reasons**.", "article_slug": None, "category_id": None,
            "created_at": NOW, "updated_at": NOW}


def _database(articles=(), claims=(), questions=(), responses=()) -> dict:
    return {
        ARTICLE_COLLECTION: FakeCollection(articles),
        CATEGORY_COLLECTION: FakeCollection([{"name": "Cosmic Canvas", "subtitle": "Science", "slug": "science", "nav_order": 1}]),
        QUESTION_COLLECTION: FakeCollection(questions),
        RESPONSE_COLLECTION: FakeCollection(responses),
        QUIZ_COLLECTION: FakeCollection(claims),
    }


def _home(database, **query) -> dict:
    return asyncio.run(get_homepage_context(database=database, **query))


def test_sections_never_repeat_a_piece_and_never_show_drafts():
    database = _database([
        _piece("story", article_format="experience", is_editors_pick=True, author_id="m1"),
        _piece("featured-story", article_format="experience", is_featured=True, days_ago=9),
        _piece("pick", is_editors_pick=True),
        _piece("member-piece", author_id="m1"),
        _piece("draft-story", article_format="experience", status="draft"),
    ])
    home = _home(database)
    slugs = {section: [card["slug"] for card in home[section]] for section in ("experiences", "ideas", "community")}
    assert slugs["experiences"] == ["featured-story", "story"]  # featured first, then newest
    assert slugs["ideas"] == ["pick"]  # "story" is a pick too, but already shown above
    assert slugs["community"] == ["member-piece"]  # only member-written pieces
    assert "draft-story" not in sum(slugs.values(), [])


def test_empty_site_hides_sections_but_keeps_rooms():
    home = _home(_database())
    assert home["question"] is None and home["arcade"] is None
    assert home["experiences"] == home["ideas"] == home["community"] == []
    assert [room["slug"] for room in home["rooms"]] == ["science"]


def test_arcade_hides_the_answer_until_chosen_and_answers_on_the_homepage():
    database = _database(claims=[_claim("myth")])
    unanswered = _home(database)["arcade"]
    assert unanswered["is_answered"] is False and "truth_label" not in unanswered
    assert unanswered["fiction_url"] == "/?claim=myth&answer=fiction#arcade"

    answered = _home(database, claim_slug="myth", answer="fiction")["arcade"]
    assert answered["is_correct"] is True and answered["truth_label"] == "Fiction"
    assert answered["next_url"] == "/?after=myth#arcade"


def test_a_drafted_claim_reveals_nothing():
    database = _database(claims=[_claim("secret", status="draft"), _claim("live")])
    arcade = _home(database, claim_slug="secret", answer="fact")["arcade"]
    assert arcade["claim"] == "Claim live is surprising." and arcade["is_answered"] is False


def test_todays_question_shows_a_featured_response_as_plain_text():
    question = {"_id": "q1", "text": "Is wisdom teachable?", "slug": "q-wisdom", "publish_date": site_today(),
                "status": "published", "intro": None, "category_id": "science", "created_at": NOW, "updated_at": NOW}
    response = {"question_id": "q1", "user_id": "u1", "author": "Mira", "author_username": "mira", "kind": "thought",
                "body": "**Wisdom** is <b>knowing</b> which questions matter.", "sources": [], "is_featured": True,
                "status": "published", "created_at": NOW, "updated_at": NOW}
    home = _home(_database(questions=[question], responses=[response]))
    assert home["question"]["room"] == "Cosmic Canvas" and home["question"]["response_count"] == 1
    # Markdown marks are stripped; the template escapes the rest.
    assert home["question"]["featured"]["body"] == "Wisdom is <b>knowing</b> which questions matter."


def test_homepage_still_stands_up_without_a_database():
    # No connection in tests, so get_database() raises; the page falls back to the launch rooms.
    home = asyncio.run(get_homepage_context())
    assert home["arcade"] is None and len(home["rooms"]) == 6
