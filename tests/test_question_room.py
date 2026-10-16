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
