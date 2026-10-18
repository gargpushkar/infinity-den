"""The Question Room: "today", response rules, moderation, privacy of hidden posts."""

import asyncio
import dataclasses
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.question import QUESTION_COLLECTION, RESPONSE_COLLECTION
from app.schemas.question import AdminResponseUpdate, QuestionRead, ResponseInput
from app.schemas.user import MemberRead
from app.services import question_service
from app.services.question_service import QuestionService, question_slug, site_today
from tests.fakes import FakeCollection


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)
MIRA = MemberRead(_id="0123456789abcdef01234567", username="mira", display_name="Mira", email="m@x.org", created_at=NOW)
SAM = MemberRead(_id="fedcba9876543210fedcba98", username="sam", display_name="Sam", email="s@x.org", created_at=NOW)


def _question(publish_date: str, *, status: str = "published", text: str = "A question worth asking?") -> dict:
    return {
        "text": text,
        "slug": question_slug(text, publish_date),
        "publish_date": publish_date,
        "status": status,
        "intro": None,
        "category_id": None,
        "created_at": NOW,
        "updated_at": NOW,
    }


def _service(questions=(), responses=()) -> QuestionService:
    return QuestionService(
        database={
            QUESTION_COLLECTION: FakeCollection(questions),
            RESPONSE_COLLECTION: FakeCollection(responses, unique=("question_id", "user_id")),
        }
    )


def _run(coroutine):
    return asyncio.run(coroutine)


# --- what "today" means ----------------------------------------------------------

def test_today_follows_the_site_timezone(monkeypatch):
    # 02:00 UTC on the 17th is still the evening of the 16th in New York.
    moment = datetime(2026, 10, 17, 2, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(question_service, "settings", dataclasses.replace(question_service.settings, site_timezone="America/New_York"))
    assert site_today(moment) == "2026-10-16"
    monkeypatch.setattr(question_service, "settings", dataclasses.replace(question_service.settings, site_timezone="UTC"))
    assert site_today(moment) == "2026-10-17"


def test_current_question_is_todays_or_the_latest_past_one():
    service = _service([
        _question("2026-10-14", text="Two days ago?"),
        _question("2026-10-15", text="Yesterday's question?"),
        _question("2026-10-17", text="Tomorrow's question?"),
        _question("2026-10-16", status="draft", text="Today's unfinished draft?"),
    ])
    # Nothing published for today: the latest past question, never a draft or a future one.
    assert _run(service.current_question("2026-10-16")).text == "Yesterday's question?"
    assert _run(service.get_live_question(question_slug("Tomorrow's question?", "2026-10-17"), "2026-10-16")) is None


# --- response rules ----------------------------------------------------------------

def test_short_thoughts_are_short():
    ResponseInput(kind="thought", body="x" * 500)
    with pytest.raises(ValidationError):
        ResponseInput(kind="thought", body="x" * 501)
    ResponseInput(kind="answer", body="x" * 3000)


def test_researched_answers_need_a_source():
    with pytest.raises(ValidationError):
        ResponseInput(kind="researched", body="Studies say so.")
    ResponseInput(kind="researched", body="Studies say so.", sources=[{"title": "A study", "url": "https://example.org"}])


def test_unknown_kind_is_rejected():
    with pytest.raises(ValidationError):
        ResponseInput(kind="rant", body="Hello there")


# --- one response per member, editors' decisions stick ---------------------------

def _live_question(service: QuestionService) -> QuestionRead:
    return _run(service.current_question("2026-10-16"))


def test_one_response_per_member_editing_replaces_it():
    service = _service([_question("2026-10-16")])
    question = _live_question(service)
    _run(service.save_response(question, MIRA, ResponseInput(kind="answer", body="First thought.")))
    _run(service.save_response(question, MIRA, ResponseInput(kind="answer", body="Second thought.")))
    responses = _run(service.public_responses(question.id))
    assert [r.body for r in responses] == ["Second thought."]


def test_hidden_responses_never_appear_and_stay_hidden_after_editing():
    service = _service([_question("2026-10-16")])
    question = _live_question(service)
    mine = _run(service.save_response(question, MIRA, ResponseInput(kind="answer", body="Off-topic.")))
    _run(service.moderate_response(mine.id, AdminResponseUpdate(status="hidden")))
    _run(service.save_response(question, MIRA, ResponseInput(kind="answer", body="Edited to sneak back.")))
    assert _run(service.public_responses(question.id)) == []
    assert _run(service.member_response(question.id, MIRA)).status == "hidden"


def test_featured_responses_come_first():
    service = _service([_question("2026-10-16")])
    question = _live_question(service)
    _run(service.save_response(question, MIRA, ResponseInput(kind="answer", body="Insightful.")))
    sams = _run(service.save_response(question, SAM, ResponseInput(kind="answer", body="Newer but ordinary.")))
    mira_id = _run(service.member_response(question.id, MIRA)).id
    _run(service.moderate_response(mira_id, AdminResponseUpdate(is_featured=True)))
    assert [r.author for r in _run(service.public_responses(question.id))] == ["Mira", "Sam"]
    assert sams.is_featured is False


def test_members_only_delete_their_own_response():
    service = _service([_question("2026-10-16")])
    question = _live_question(service)
    _run(service.save_response(question, MIRA, ResponseInput(kind="answer", body="Mine.")))
    assert _run(service.delete_response(question.id, SAM)) is False
    assert len(_run(service.public_responses(question.id))) == 1
    assert _run(service.delete_response(question.id, MIRA)) is True


def test_question_slug_is_dated_and_readable():
    assert question_slug("Can a person be intelligent without being wise?", "2026-10-16") == (
        "2026-10-16-can-a-person-be-intelligent-without-being-wise"
    )


# --- the page: filters, featured quotes, folding ------------------------------------

def _page_context(monkeypatch, service: QuestionService, **kwargs):
    from app.services import question_page_service

    async def no_rooms(_db):
        return [{"slug": "science", "name": "Cosmic Canvas"}]

    monkeypatch.setattr(question_page_service, "get_database", lambda: service.database)
    monkeypatch.setattr(question_page_service, "get_rooms", no_rooms)
    monkeypatch.setattr(question_page_service, "site_today", lambda: "2026-10-16")
    return _run(question_page_service.get_question_room_context(slug=None, member=None, **kwargs))


def _members(count: int) -> list[MemberRead]:
    return [MemberRead(_id=f"{n:024x}", username=f"m{n}", display_name=f"M{n}", email=f"{n}@x.org", created_at=NOW) for n in range(1, count + 1)]


def test_featured_responses_lead_and_the_list_folds_after_eight(monkeypatch):
    service = _service([_question("2026-10-16"), {**_question("2026-10-15", text="Yesterday's question?"), "category_id": "science"}])
    question = _live_question(service)
    for member in _members(11):
        _run(service.save_response(question, member, ResponseInput(kind="answer", body=f"Answer from {member.display_name}.")))
    first = _run(service.member_response(question.id, _members(1)[0]))
    _run(service.moderate_response(first.id, AdminResponseUpdate(is_featured=True)))

    context = _page_context(monkeypatch, service)
    assert [r["author"] for r in context["featured_responses"]] == ["M1"]
    assert len(context["responses_shown"]) == 8 and len(context["responses_folded"]) == 2  # the other 10
    assert "M1" not in [r["author"] for r in context["responses_shown"] + context["responses_folded"]]
    past = context["past_questions"][0]
    assert (past["day"], past["month"], past["room_name"]) == (15, "October", "Cosmic Canvas")


def test_a_kind_filter_lists_only_that_kind_featured_included(monkeypatch):
    service = _service([_question("2026-10-16")])
    question = _live_question(service)
    people = _members(3)
    _run(service.save_response(question, people[0], ResponseInput(kind="thought", body="Dark matter.")))
    _run(service.save_response(question, people[1], ResponseInput(kind="story", body="My son's condition.")))
    featured = _run(service.save_response(question, people[2], ResponseInput(kind="thought", body="Life starting twice.")))
    _run(service.moderate_response(featured.id, AdminResponseUpdate(is_featured=True)))

    context = _page_context(monkeypatch, service, kind="thought")
    assert context["active_kind"] == "thought" and context["featured_responses"] == []
    assert sorted(r["author"] for r in context["responses_shown"]) == ["M1", "M3"]
    assert {f["value"]: f["count"] for f in context["kind_filters"]} == {"thought": 2, "answer": 0, "story": 1, "researched": 0}
    assert _page_context(monkeypatch, service, kind="nonsense")["active_kind"] == ""
