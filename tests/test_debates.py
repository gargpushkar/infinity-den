"""The Debate Den: open and closed debates, argument and rebuttal rules, moderation, ordering, unsafe HTML."""

import asyncio
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.debate import ARGUMENT_COLLECTION, DEBATE_COLLECTION, REBUTTAL_COLLECTION
from app.schemas.debate import AdminArgumentUpdate, AdminRebuttalUpdate, ArgumentInput, DebateInput, RebuttalInput
from app.schemas.user import MemberRead
from app.services.debate_page_service import _argument_view, _rebuttal_view, _with_thread
from app.services.debate_service import (
    DebateClosedError,
    DebateNotFoundError,
    DebateService,
    OwnArgumentError,
    debate_slug,
    is_open,
)
from tests.fakes import FakeCollection


NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)
TODAY = "2026-10-16"
MIRA = MemberRead(_id="0123456789abcdef01234567", username="mira", display_name="Mira", email="m@x.org", created_at=NOW)
SAM = MemberRead(_id="fedcba9876543210fedcba98", username="sam", display_name="Sam", email="s@x.org", created_at=NOW)
LEE = MemberRead(_id="0000000000000000000000ee", username="lee", display_name="Lee", email="l@x.org", created_at=NOW)
CASE = "Long commutes cost cities more in lost time and emissions than offices ever save."


def _run(coroutine):
    return asyncio.run(coroutine)


def _service() -> DebateService:
    return DebateService(database={
        DEBATE_COLLECTION: FakeCollection(),
        ARGUMENT_COLLECTION: FakeCollection(unique=("debate_id", "user_id")),
        REBUTTAL_COLLECTION: FakeCollection(unique=("argument_id", "user_id")),
    })


def _debate(service: DebateService, *, closes_on: str = "2026-10-30", status: str = "published"):
    return _run(service.create_debate(DebateInput(
        motion="This house believes remote work is better for society", closes_on=closes_on, status=status,
    )))


def _argue(side: str = "for", claim: str = "Commutes cost more", body: str = CASE) -> ArgumentInput:
    return ArgumentInput(side=side, claim=claim, body=body)


# --- open, closed, drafts -------------------------------------------------------

def test_a_debate_is_open_through_its_closing_day_and_drafts_are_never_open():
    service = _service()
    assert is_open(_debate(service, closes_on=TODAY), TODAY)
    assert not is_open(_debate(service, closes_on="2026-10-15"), TODAY)
    assert not is_open(_debate(service, status="draft"), TODAY)


def test_drafts_are_not_public():
    service = _service()
    draft = _debate(service, status="draft")
    assert _run(service.get_published_debate(draft.slug)) is None
    assert _run(service.published_debates()) == []


def test_closed_debates_take_no_new_arguments_or_edits():
    service = _service()
    debate = _debate(service, closes_on="2026-10-15")
    with pytest.raises(DebateClosedError):
        _run(service.save_argument(debate, MIRA, _argue(), TODAY))


def test_slug_is_readable_and_unique():
    slug = debate_slug("This house believes remote work is better!")
    assert slug.startswith("this-house-believes-remote-work-is-better-")
    assert slug != debate_slug("This house believes remote work is better!")


# --- argument rules -------------------------------------------------------------

def test_arguments_need_a_side_a_claim_and_a_real_case():
    with pytest.raises(ValidationError):
        _argue(side="maybe")
    with pytest.raises(ValidationError):
        _argue(claim="Short")
    with pytest.raises(ValidationError):
        _argue(body="Too short to be a case.")
    with pytest.raises(ValidationError):
        _argue(claim="x" * 151)
    _argue()  # sources are optional


def test_one_argument_per_member_and_editing_can_switch_sides():
    service = _service()
    debate = _debate(service)
    _run(service.save_argument(debate, MIRA, _argue("for"), TODAY))
    _run(service.save_argument(debate, MIRA, _argue("against", claim="On reflection, offices win"), TODAY))
    arguments = _run(service.public_arguments(debate.id))
    assert [(a.side, a.claim) for a in arguments] == [("against", "On reflection, offices win")]


def test_hidden_arguments_stay_hidden_after_editing_and_featured_come_first():
    service = _service()
    debate = _debate(service)
    mira = _run(service.save_argument(debate, MIRA, _argue(), TODAY))
    sam = _run(service.save_argument(debate, SAM, _argue("against", claim="Juniors learn by watching"), TODAY))
    _run(service.moderate_argument(mira.id, AdminArgumentUpdate(status="hidden")))
    _run(service.save_argument(debate, MIRA, _argue(claim="Edited to sneak back in"), TODAY))
    assert [a.author for a in _run(service.public_arguments(debate.id))] == ["Sam"]
    assert _run(service.member_argument(debate.id, MIRA)).status == "hidden"

    _run(service.moderate_argument(mira.id, AdminArgumentUpdate(status="published")))
    _run(service.moderate_argument(sam.id, AdminArgumentUpdate(is_featured=True)))
    assert [a.author for a in _run(service.public_arguments(debate.id))] == ["Sam", "Mira"]
    assert _run(service.argument_counts([debate.id])) == {debate.id: 2}


def test_members_only_delete_their_own_argument_and_deleting_a_debate_removes_its_arguments():
    service = _service()
    debate = _debate(service)
    _run(service.save_argument(debate, MIRA, _argue(), TODAY))
    assert _run(service.delete_argument(debate.id, SAM)) is False
    assert _run(service.delete_argument(debate.id, MIRA)) is True
    _run(service.save_argument(debate, SAM, _argue(), TODAY))
    assert _run(service.delete_debate(debate.id)) is True
    assert service.arguments.documents == []


@pytest.mark.parametrize("attack", ["<script>alert(1)</script>", "[x](javascript:alert(1))", "<img src=x onerror=alert(1)>"])
def test_argument_html_is_never_rendered(attack):
    service = _service()
    argument = _run(service.save_argument(_debate(service), MIRA, _argue(body=CASE + attack), TODAY))
    html = str(_argument_view(argument)["body_html"])
    assert "<script" not in html and "<img" not in html and 'href="javascript' not in html


# --- rebuttals ----------------------------------------------------------------

REPLY = RebuttalInput(body="Your source counts car commutes only.")


def _debate_with_argument(service: DebateService, closes_on: str = "2026-10-30"):
    debate = _debate(service, closes_on=closes_on)
    argument = _run(service.save_argument(debate, MIRA, _argue(), TODAY))
    return debate, argument


def test_rebuttals_are_short_and_never_on_your_own_argument():
    with pytest.raises(ValidationError):
        RebuttalInput(body="Nope.")
    with pytest.raises(ValidationError):
        RebuttalInput(body="x" * 1001)
    service = _service()
    debate, argument = _debate_with_argument(service)
    with pytest.raises(OwnArgumentError):
        _run(service.save_rebuttal(debate, argument.id, MIRA, REPLY, TODAY))


def test_rebuttals_need_an_open_debate_and_a_visible_argument_in_it():
    service = _service()
    debate, argument = _debate_with_argument(service)
    other = _debate(service)
    with pytest.raises(DebateNotFoundError):  # an argument from another debate
        _run(service.save_rebuttal(other, argument.id, SAM, REPLY, TODAY))
    _run(service.moderate_argument(argument.id, AdminArgumentUpdate(status="hidden")))
    with pytest.raises(DebateNotFoundError):
        _run(service.save_rebuttal(debate, argument.id, SAM, REPLY, TODAY))

    open_debate, open_argument = _debate_with_argument(service)
    closed = _run(service.update_debate(open_debate.id, DebateInput(motion=open_debate.motion, closes_on="2026-10-15", status="published")))
    with pytest.raises(DebateClosedError):
        _run(service.save_rebuttal(closed, open_argument.id, SAM, REPLY, TODAY))


def test_one_rebuttal_per_member_per_argument_oldest_first_and_hidden_stays_hidden():
    service = _service()
    debate, argument = _debate_with_argument(service)
    sams = _run(service.save_rebuttal(debate, argument.id, SAM, REPLY, TODAY))
    _run(service.save_rebuttal(debate, argument.id, LEE, RebuttalInput(body="Commute time is not all lost."), TODAY))
    _run(service.save_rebuttal(debate, argument.id, SAM, RebuttalInput(body="Edited: most remote workers took transit."), TODAY))
    thread = _run(service.public_rebuttals(debate.id))[argument.id]
    assert [(r.author, r.body) for r in thread] == [("Sam", "Edited: most remote workers took transit."), ("Lee", "Commute time is not all lost.")]

    _run(service.moderate_rebuttal(sams.id, AdminRebuttalUpdate(status="hidden")))
    _run(service.save_rebuttal(debate, argument.id, SAM, RebuttalInput(body="Edited again to sneak back in."), TODAY))
    assert [r.author for r in _run(service.public_rebuttals(debate.id))[argument.id]] == ["Lee"]
    assert _run(service.member_rebuttals(debate.id, SAM))[argument.id].status == "hidden"


def test_threads_fold_after_three_and_keep_your_hidden_rebuttal_visible_to_you():
    service = _service()
    debate, argument = _debate_with_argument(service)
    others = [MemberRead(_id=f"{n:024x}", username=f"m{n}", display_name=f"M{n}", email=f"{n}@x.org", created_at=NOW) for n in range(1, 5)]
    for member in others:
        _run(service.save_rebuttal(debate, argument.id, member, REPLY, TODAY))
    mine = _run(service.save_rebuttal(debate, argument.id, SAM, REPLY, TODAY))
    _run(service.moderate_rebuttal(mine.id, AdminRebuttalUpdate(status="hidden")))

    public = _run(service.public_rebuttals(debate.id))[argument.id]
    view = _with_thread(_argument_view(argument), public, _run(service.member_rebuttals(debate.id, SAM))[argument.id])
    assert view["rebuttal_count"] == 4 and len(view["rebuttals_shown"]) == 3
    assert [r["is_hidden"] for r in view["rebuttals_folded"]] == [False, True]
    assert view["own_rebuttal"]["id"] == mine.id and view["own_rebuttal_folded"] is True


def test_deleting_an_argument_or_debate_removes_its_rebuttals():
    service = _service()
    debate, argument = _debate_with_argument(service)
    _run(service.save_rebuttal(debate, argument.id, SAM, REPLY, TODAY))
    assert _run(service.delete_rebuttal(argument.id, LEE)) is False  # only your own
    assert _run(service.delete_argument(debate.id, MIRA)) is True
    assert service.rebuttals.documents == []

    debate, argument = _debate_with_argument(service)
    _run(service.save_rebuttal(debate, argument.id, SAM, REPLY, TODAY))
    _run(service.delete_debate(debate.id))
    assert service.rebuttals.documents == []


@pytest.mark.parametrize("attack", ["<script>alert(1)</script>", "[x](javascript:alert(1))", "<img src=x onerror=alert(1)>"])
def test_rebuttal_html_is_never_rendered(attack):
    service = _service()
    debate, argument = _debate_with_argument(service)
    rebuttal = _run(service.save_rebuttal(debate, argument.id, SAM, RebuttalInput(body="A careful reply. " + attack), TODAY))
    html = str(_rebuttal_view(rebuttal)["body_html"])
    assert "<script" not in html and "<img" not in html and 'href="javascript' not in html


def test_only_a_real_edit_by_the_author_marks_an_argument_or_rebuttal_edited():
    service = _service()
    debate, argument = _debate_with_argument(service)
    assert _argument_view(argument)["edited_label"] is None

    _run(service.moderate_argument(argument.id, AdminArgumentUpdate(is_featured=True)))  # editors' actions don't count
    _run(service.save_argument(debate, MIRA, _argue(), TODAY))  # saving the same words doesn't either
    assert _run(service.member_argument(debate.id, MIRA)).edited_at is None

    edited = _run(service.save_argument(debate, MIRA, _argue(claim="Commutes cost even more"), TODAY))
    assert edited.edited_at is not None and _argument_view(edited)["edited_label"]

    rebuttal = _run(service.save_rebuttal(debate, argument.id, SAM, REPLY, TODAY))
    _run(service.moderate_rebuttal(rebuttal.id, AdminRebuttalUpdate(status="hidden")))
    assert _run(service.save_rebuttal(debate, argument.id, SAM, REPLY, TODAY)).edited_at is None
    changed = _run(service.save_rebuttal(debate, argument.id, SAM, RebuttalInput(body="A sharper version of my reply."), TODAY))
    assert _rebuttal_view(changed)["edited_label"]
