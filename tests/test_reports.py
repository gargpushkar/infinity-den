"""Reports: who can report what, one open report per member, and what editors' decisions do."""

import asyncio
from datetime import datetime, timezone

import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.models.article import ARTICLE_COLLECTION
from app.models.comment import COMMENT_COLLECTION
from app.models.debate import ARGUMENT_COLLECTION, DEBATE_COLLECTION, REBUTTAL_COLLECTION
from app.models.question import QUESTION_COLLECTION, RESPONSE_COLLECTION
from app.models.report import REPORT_COLLECTION
from app.schemas.admin import AdminRead
from app.schemas.report import ReportAction, ReportInput
from app.schemas.user import MemberRead
from app.services.report_service import OwnContentError, ReportService, ReportTargetNotFoundError
from tests.fakes import FakeCollection


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)
MIRA = MemberRead(_id="0123456789abcdef01234567", username="mira", display_name="Mira", email="m@x.org", created_at=NOW)
SAM = MemberRead(_id="fedcba9876543210fedcba98", username="sam", display_name="Sam", email="s@x.org", created_at=NOW)
LEE = MemberRead(_id="0000000000000000000000ee", username="lee", display_name="Lee", email="l@x.org", created_at=NOW)
EDITOR = AdminRead(_id="0000000000000000000000ad", username="editor", role="editor", created_at=NOW)

ARTICLE, QUESTION, RESPONSE, COMMENT, DRAFT, DEBATE, ARGUMENT, REBUTTAL = (ObjectId() for _ in range(8))


def _run(coroutine):
    return asyncio.run(coroutine)


def _service() -> ReportService:
    return ReportService(database={
        ARTICLE_COLLECTION: FakeCollection([
            {"_id": ARTICLE, "title": "The Ship of Theseus", "slug": "theseus", "author": "Sam", "author_id": SAM.id, "status": "published"},
            {"_id": DRAFT, "title": "Unfinished", "slug": "draft", "author": "Sam", "author_id": SAM.id, "status": "draft"},
        ]),
        QUESTION_COLLECTION: FakeCollection([{"_id": QUESTION, "slug": "q-wisdom"}]),
        RESPONSE_COLLECTION: FakeCollection([{"_id": RESPONSE, "question_id": str(QUESTION), "user_id": SAM.id, "author": "Sam", "body": "An answer.", "status": "published"}]),
        COMMENT_COLLECTION: FakeCollection([{"_id": COMMENT, "article_id": str(ARTICLE), "user_id": SAM.id, "author": "Sam", "body": "Buy pills.", "status": "published"}]),
        DEBATE_COLLECTION: FakeCollection([{"_id": DEBATE, "slug": "remote-work-1a2b"}]),
        ARGUMENT_COLLECTION: FakeCollection([{"_id": ARGUMENT, "debate_id": str(DEBATE), "user_id": SAM.id, "author": "Sam", "claim": "Commutes cost more", "body": "Because.", "status": "published"}]),
        REBUTTAL_COLLECTION: FakeCollection([{"_id": REBUTTAL, "debate_id": str(DEBATE), "argument_id": str(ARGUMENT), "user_id": SAM.id, "author": "Sam", "body": "Not so.", "status": "published"}]),
        REPORT_COLLECTION: FakeCollection(),
    })


def _report(target_type: str, target_id: ObjectId, reason: str = "spam", detail: str | None = None) -> ReportInput:
    return ReportInput(target_type=target_type, target_id=str(target_id), reason=reason, detail=detail)


def test_reasons_are_checked_and_something_else_needs_a_note():
    with pytest.raises(ValidationError):
        _report("comment", COMMENT, reason="boring")
    with pytest.raises(ValidationError):
        _report("comment", COMMENT, reason="other")
    _report("comment", COMMENT, reason="other", detail="Off-topic advert.")
    with pytest.raises(ValidationError):
        ReportInput(target_type="comment", target_id="not-an-id", reason="spam")


def test_targets_link_to_where_they_appear():
    service = _service()
    assert _run(service.target("comment", str(COMMENT)))["url"] == f"/articles/theseus#comment-{COMMENT}"
    assert _run(service.target("response", str(RESPONSE)))["url"] == f"/questions/q-wisdom#response-{RESPONSE}"
    assert _run(service.target("article", str(ARTICLE)))["url"] == "/articles/theseus"
    argument = _run(service.target("argument", str(ARGUMENT)))
    assert argument["url"] == f"/debates/remote-work-1a2b#argument-{ARGUMENT}" and argument["text"].startswith("Commutes cost more")
    assert _run(service.target("rebuttal", str(REBUTTAL)))["url"] == f"/debates/remote-work-1a2b#rebuttal-{REBUTTAL}"


def test_members_cannot_report_their_own_work_or_unpublished_items():
    service = _service()
    with pytest.raises(OwnContentError):
        _run(service.submit(SAM, _report("comment", COMMENT)))
    with pytest.raises(ReportTargetNotFoundError):
        _run(service.submit(MIRA, _report("article", DRAFT)))
    with pytest.raises(ReportTargetNotFoundError):
        _run(service.submit(MIRA, _report("comment", ObjectId())))


def test_reporting_again_updates_the_open_report():
    service = _service()
    _run(service.submit(MIRA, _report("comment", COMMENT, reason="spam")))
    _run(service.submit(MIRA, _report("comment", COMMENT, reason="harassment")))
    reports = service.reports.documents
    assert len(reports) == 1 and reports[0]["reason"] == "harassment"


def test_queue_groups_by_item_most_reported_first():
    service = _service()
    _run(service.submit(MIRA, _report("article", ARTICLE, reason="misinformation")))
    _run(service.submit(MIRA, _report("comment", COMMENT)))
    _run(service.submit(LEE, _report("comment", COMMENT)))
    queue = _run(service.queue())
    assert [(item["target_type"], item["count"]) for item in queue] == [("comment", 2), ("article", 1)]
    assert queue[0]["reasons"] == [("Spam or advertising", 2)]


def test_hiding_closes_every_open_report_and_hides_the_item():
    service = _service()
    _run(service.submit(MIRA, _report("comment", COMMENT)))
    _run(service.submit(LEE, _report("comment", COMMENT)))
    closed = _run(service.act(ReportAction(target_type="comment", target_id=str(COMMENT), action="hide"), EDITOR))
    assert closed == 2 and _run(service.queue()) == []
    assert service.database[COMMENT_COLLECTION].documents[0]["status"] == "hidden"
    assert {r["status"] for r in service.reports.documents} == {"resolved"}
    assert _run(service.recently_handled())[0]["report"].resolved_by == "editor"


def test_hiding_an_article_archives_it_and_dismissing_changes_nothing():
    service = _service()
    _run(service.submit(MIRA, _report("response", RESPONSE)))
    _run(service.act(ReportAction(target_type="response", target_id=str(RESPONSE), action="dismiss"), EDITOR))
    assert service.database[RESPONSE_COLLECTION].documents[0]["status"] == "published"
    assert service.reports.documents[0]["status"] == "dismissed"

    _run(service.submit(MIRA, _report("article", ARTICLE)))
    _run(service.act(ReportAction(target_type="article", target_id=str(ARTICLE), action="hide"), EDITOR))
    assert service.database[ARTICLE_COLLECTION].documents[0]["status"] == "archived"
