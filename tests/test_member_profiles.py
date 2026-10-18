"""Member profiles: strengths earned from ratings and editors' picks, never popularity; blind averages stay blind."""

import asyncio
from datetime import datetime, timezone

from bson import ObjectId

from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.models.debate import ARGUMENT_COLLECTION, DEBATE_COLLECTION, RATING_COLLECTION, REBUTTAL_COLLECTION, STANCE_COLLECTION
from app.models.question import QUESTION_COLLECTION, RESPONSE_COLLECTION
from app.models.user import USER_COLLECTION
from app.schemas.debate import AdminRebuttalUpdate
from app.services import member_page_service
from app.services.debate_service import DebateService
from app.services.member_reputation_service import earned_strengths
from tests.fakes import FakeCollection


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def _rated(clarity: float, evidence: float, reasoning: float, count: int = 3) -> dict:
    return {"count": count, "clarity": clarity, "evidence": evidence, "reasoning": reasoning}


def _labels(**kwargs) -> list[str]:
    defaults = {"rated_arguments": [], "researched_pieces": 0, "featured": 0, "thoughtful_rebuttals": 0}
    return [s["label"] for s in earned_strengths(**{**defaults, **kwargs})]


# --- earning strengths ---------------------------------------------------------------

def test_rated_strengths_need_three_well_rated_arguments():
    assert _labels(rated_arguments=[_rated(5, 5, 5)] * 2) == []  # too few arguments
    assert _labels(rated_arguments=[_rated(4.5, 3.0, 4.0)] * 3) == ["Clear explainer", "Sound reasoning"]
    assert _labels(rated_arguments=[_rated(5, 5, 5, count=2)] * 5) == []  # each needs 3 ratings


def test_strength_reasons_name_the_average_and_never_use_pronouns():
    strengths = earned_strengths(rated_arguments=[_rated(4.2, 4.6, 4.0)] * 4, researched_pieces=3, featured=2, thoughtful_rebuttals=1)
    details = {s["label"]: s["detail"] for s in strengths}
    assert details["Well-sourced"] == "Evidence rated 4.6 across 4 arguments, and 3 researched pieces published"
    assert details["Editor's pick"] == "2 contributions featured by editors"
    assert details["Thoughtful rebuttals"] == "1 rebuttal marked thoughtful by editors"
    assert not any(word in " ".join(details.values()).lower().split() for word in ("her", "his", "their", "she", "he", "they"))


def test_researched_pieces_alone_can_earn_well_sourced():
    assert _labels(researched_pieces=3) == ["Well-sourced"]
    assert _labels(researched_pieces=2) == []


# --- the profile page ---------------------------------------------------------------

MIRA = ObjectId()


def _world() -> dict:
    mira = str(MIRA)
    open_debate, closed_debate, draft = ObjectId(), ObjectId(), ObjectId()
    debates = [
        {"_id": open_debate, "motion": "Open motion", "slug": "open-1", "closes_on": "2999-01-01", "status": "published", "intro": None, "category_id": None, "created_at": NOW},
        {"_id": closed_debate, "motion": "Closed motion", "slug": "closed-1", "closes_on": "2000-01-01", "status": "published", "intro": None, "category_id": None, "created_at": NOW},
        {"_id": draft, "motion": "Draft motion", "slug": "draft-1", "closes_on": "2999-01-01", "status": "draft", "intro": None, "category_id": None, "created_at": NOW},
    ]

    def argument(debate, claim, featured=False):
        return {"_id": ObjectId(), "debate_id": str(debate), "user_id": mira, "author": "Mira", "author_username": "mira", "side": "for",
                "claim": claim, "body": "A case long enough.", "sources": [], "is_featured": featured, "status": "published",
                "created_at": NOW, "updated_at": NOW}
    in_open, in_closed, in_draft = argument(open_debate, "Open claim", featured=True), argument(closed_debate, "Closed claim"), argument(draft, "Draft claim")
    ratings = [{"debate_id": str(d), "argument_id": str(a["_id"]), "user_id": f"rater{n}", "clarity": 5, "evidence": 4, "reasoning": 4}
               for a, d in ((in_open, open_debate), (in_closed, closed_debate)) for n in range(3)]
    rebuttal = {"_id": ObjectId(), "debate_id": str(closed_debate), "argument_id": str(in_closed["_id"]), "user_id": mira, "author": "Mira",
                "author_username": "mira", "body": "A thoughtful reply.", "is_featured": False, "status": "published", "created_at": NOW, "updated_at": NOW}
    user = {"_id": MIRA, "username": "mira", "display_name": "Mira", "email": "m@x.org", "password_hash": "x", "bio": None,
            "is_active": True, "created_at": NOW, "updated_at": NOW}
    return {
        USER_COLLECTION: FakeCollection([user]),
        ARTICLE_COLLECTION: FakeCollection(),
        CATEGORY_COLLECTION: FakeCollection(),
        QUESTION_COLLECTION: FakeCollection(),
        RESPONSE_COLLECTION: FakeCollection(),
        DEBATE_COLLECTION: FakeCollection(debates),
        ARGUMENT_COLLECTION: FakeCollection([in_open, in_closed, in_draft]),
        RATING_COLLECTION: FakeCollection(ratings),
        REBUTTAL_COLLECTION: FakeCollection([rebuttal]),
        STANCE_COLLECTION: FakeCollection(),
    }


def _profile(monkeypatch, db, viewer=None):
    async def no_rooms(_db):
        return []

    async def no_pieces(self, query):
        return type("Listing", (), {"items": [], "total": 0})()

    monkeypatch.setattr(member_page_service, "get_database", lambda: db)
    monkeypatch.setattr(member_page_service, "get_rooms", no_rooms)
    monkeypatch.setattr(member_page_service.ArticleService, "list_articles", no_pieces)
    return asyncio.run(member_page_service.get_member_profile_context("mira", viewer=viewer))


def test_profile_lists_arguments_but_keeps_open_debates_blind_and_drafts_out(monkeypatch):
    profile = _profile(monkeypatch, _world())
    arguments = {a["claim"]: a for a in profile["arguments_shown"]}
    assert set(arguments) == {"Open claim", "Closed claim"}  # the draft debate's argument stays out
    assert arguments["Open claim"]["rating"] is None and arguments["Open claim"]["is_open"]
    assert arguments["Closed claim"]["rating"]["clarity"] == 5.0
    assert profile["counts"] == {"pieces": 0, "responses": 0, "arguments": 2, "rebuttals": 1}
    assert [s["label"] for s in profile["strengths"]] == ["Editor's pick"]  # one closed rated argument isn't enough
    assert profile["is_own"] is False and "email" not in profile["member"]


def test_a_rebuttal_editors_mark_thoughtful_shows_on_the_profile(monkeypatch):
    db = _world()
    rebuttal_id = str(db[REBUTTAL_COLLECTION].documents[0]["_id"])
    asyncio.run(DebateService(database=db).moderate_rebuttal(rebuttal_id, AdminRebuttalUpdate(is_featured=True)))
    profile = _profile(monkeypatch, db)
    assert [r["argument_claim"] for r in profile["thoughtful_rebuttals"]] == ["Closed claim"]
    assert "Thoughtful rebuttals" in [s["label"] for s in profile["strengths"]]


def test_only_the_owner_sees_their_profile_as_their_own(monkeypatch):
    from app.schemas.user import MemberRead

    owner = MemberRead(_id=str(MIRA), username="mira", display_name="Mira", email="m@x.org", created_at=NOW)
    assert _profile(monkeypatch, _world(), viewer=owner)["is_own"] is True
