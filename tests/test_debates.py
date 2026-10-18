"""The Debate Den: open and closed debates, argument and rebuttal rules, moderation, ordering, unsafe HTML."""

import asyncio
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.debate import ARGUMENT_COLLECTION, DEBATE_COLLECTION, RATING_COLLECTION, REBUTTAL_COLLECTION, STANCE_COLLECTION
from app.schemas.debate import (
    AdminArgumentUpdate,
    AdminRebuttalUpdate,
    AdminStanceUpdate,
    ArgumentInput,
    DebateInput,
    RatingInput,
    RebuttalInput,
    StanceAfterInput,
    StanceBeforeInput,
)
from app.schemas.user import MemberRead
from app.services.debate_page_service import _argument_view, _rebuttal_view, _with_rating, _with_thread
from app.services.debate_rating_service import DebateRatingService
from app.services.debate_stance_service import DebateStanceService, StanceLockedError
from app.services.debate_page_service import results_view
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
        RATING_COLLECTION: FakeCollection(unique=("argument_id", "user_id")),
        STANCE_COLLECTION: FakeCollection(unique=("debate_id", "user_id")),
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



# --- ratings ------------------------------------------------------------------

def _member(n: int) -> MemberRead:
    return MemberRead(_id=f"{n:024x}", username=f"m{n}", display_name=f"M{n}", email=f"{n}@x.org", created_at=NOW)


def _rate(clarity: int, evidence: int, reasoning: int) -> RatingInput:
    return RatingInput(clarity=clarity, evidence=evidence, reasoning=reasoning)


def test_all_three_scores_are_required_and_between_1_and_5():
    with pytest.raises(ValidationError):
        RatingInput(clarity="", evidence=3, reasoning=3)
    with pytest.raises(ValidationError):
        _rate(6, 3, 3)
    with pytest.raises(ValidationError):
        _rate(0, 3, 3)
    assert RatingInput(clarity="4", evidence="3", reasoning="5").clarity == 4  # form values arrive as text


def test_no_rating_your_own_argument_a_hidden_one_or_after_the_debate_closes():
    service = _service()
    ratings = DebateRatingService(database=service.database)
    debate, argument = _debate_with_argument(service)
    with pytest.raises(OwnArgumentError):
        _run(ratings.save_rating(debate, argument.id, MIRA, _rate(5, 5, 5), TODAY))
    closed = _run(service.update_debate(debate.id, DebateInput(motion=debate.motion, closes_on="2026-10-15", status="published")))
    with pytest.raises(DebateClosedError):
        _run(ratings.save_rating(closed, argument.id, SAM, _rate(4, 4, 4), TODAY))
    _run(service.moderate_argument(argument.id, AdminArgumentUpdate(status="hidden")))
    with pytest.raises(DebateNotFoundError):
        _run(ratings.save_rating(debate, argument.id, SAM, _rate(4, 4, 4), TODAY))


def test_one_rating_per_member_changing_it_replaces_it_and_averages_round_to_one_decimal():
    service = _service()
    ratings = DebateRatingService(database=service.database)
    debate, argument = _debate_with_argument(service)
    _run(ratings.save_rating(debate, argument.id, SAM, _rate(1, 1, 1), TODAY))
    _run(ratings.save_rating(debate, argument.id, SAM, _rate(5, 4, 3), TODAY))  # changed their mind
    _run(ratings.save_rating(debate, argument.id, LEE, _rate(4, 2, 3), TODAY))
    _run(ratings.save_rating(debate, argument.id, _member(9), _rate(4, 2, 4), TODAY))
    assert _run(ratings.averages(debate.id))[argument.id] == {"count": 3, "clarity": 4.3, "evidence": 2.7, "reasoning": 3.3}
    assert _run(ratings.member_ratings(debate.id, SAM)) == {argument.id: {"clarity": 5, "evidence": 4, "reasoning": 3}}


def test_averages_need_three_ratings_and_stay_blind_until_you_rate_or_the_debate_closes():
    view = _argument_view(_debate_with_argument(_service())[1])
    two = {"count": 2, "clarity": 4.0, "evidence": 4.0, "reasoning": 4.0}
    three = {**two, "count": 3}
    mine = {"clarity": 4, "evidence": 4, "reasoning": 4}
    assert _with_rating(view, two, mine, debate_open=True)["rating"] is None        # not enough yet
    assert _with_rating(view, three, None, debate_open=True)["rating"] is None      # you haven't rated it
    assert _with_rating(view, three, mine, debate_open=True)["rating"] == three     # you have
    assert _with_rating(view, three, None, debate_open=False)["rating"] == three    # the debate closed
    assert _with_rating(view, two, None, debate_open=False)["rating"] is None       # still too few


def test_deleting_an_argument_or_debate_removes_its_ratings():
    service = _service()
    ratings = DebateRatingService(database=service.database)
    debate, argument = _debate_with_argument(service)
    _run(ratings.save_rating(debate, argument.id, SAM, _rate(3, 3, 3), TODAY))
    _run(service.delete_argument(debate.id, MIRA))
    assert service.ratings.documents == []

    debate, argument = _debate_with_argument(service)
    _run(ratings.save_rating(debate, argument.id, SAM, _rate(3, 3, 3), TODAY))
    _run(service.delete_debate(debate.id))
    assert service.ratings.documents == []



# --- stances ------------------------------------------------------------------

def _stances(service: DebateService) -> DebateStanceService:
    return DebateStanceService(database=service.database)


def _before(stance: str) -> StanceBeforeInput:
    return StanceBeforeInput(stance=stance)


def _after(stance: str, note: str | None = None) -> StanceAfterInput:
    return StanceAfterInput(stance=stance, note=note)


def test_stances_are_for_against_or_undecided_and_notes_are_short():
    with pytest.raises(ValidationError):
        _before("maybe")
    with pytest.raises(ValidationError):
        _after("for", note="x" * 501)
    assert _after("for", note="   ").note is None


def test_before_can_change_until_after_is_given_then_it_locks():
    service = _service()
    stances = _stances(service)
    debate = _debate(service)
    _run(stances.save_before(debate, SAM, _before("against"), TODAY))
    _run(stances.save_before(debate, SAM, _before("undecided"), TODAY))  # changed before reading: fine
    _run(stances.save_after(debate, SAM, _after("for"), TODAY))
    with pytest.raises(StanceLockedError):
        _run(stances.save_before(debate, SAM, _before("for"), TODAY))
    stance = _run(stances.member_stance(debate.id, SAM))
    assert (stance["before"], stance["after"]) == ("undecided", "for")


def test_no_stances_once_the_debate_closes():
    service = _service()
    debate = _debate(service, closes_on="2026-10-15")
    with pytest.raises(DebateClosedError):
        _run(_stances(service).save_before(debate, SAM, _before("for"), TODAY))
    with pytest.raises(DebateClosedError):
        _run(_stances(service).save_after(debate, SAM, _after("for"), TODAY))


def test_results_count_both_sides_and_moves_along_one_line_with_changed_minds_first():
    service = _service()
    stances = _stances(service)
    debate = _debate(service)
    people = [_member(n) for n in range(1, 7)]
    plan = [
        ("against", "for", "The commute data convinced me."),   # +2, towards For
        ("undecided", "for", None),                             # +1, towards For
        ("for", "undecided", "Less sure now."),                  # -1, towards Against
        ("for", "for", "Still for, more so."),                   # held
        (None, "against", "Came late, but against."),            # no before: counted, never "changed"
        ("against", None, None),                                 # never gave an after
    ]
    for member, (before, after, note) in zip(people, plan):
        if before:
            _run(stances.save_before(debate, member, _before(before), TODAY))
        if after:
            _run(stances.save_after(debate, member, _after(after, note), TODAY))

    results = _run(stances.results(debate.id))
    assert [(r["stance"], r["count"]) for r in results["before"]["rows"]] == [("for", 2), ("against", 2), ("undecided", 1)]
    assert [(r["stance"], r["count"]) for r in results["after"]["rows"]] == [("for", 3), ("against", 1), ("undecided", 1)]
    assert results["after"]["rows"][0]["percent"] == 60
    assert (results["changed"], results["towards_for"], results["towards_against"]) == (3, 2, 1)
    assert [n["note"] for n in results["notes"]] == [
        "The commute data convinced me.", "Less sure now.", "Still for, more so.", "Came late, but against.",
    ]
    views = results_view(results)["notes"]
    assert (views[0]["before_label"], views[0]["after_label"], views[0]["changed"]) == ("Against", "For", True)
    assert views[3]["changed"] is False and views[3]["before_label"] is None


def test_hidden_notes_leave_the_results_but_the_stance_still_counts_and_stays_hidden_after_editing():
    service = _service()
    stances = _stances(service)
    debate = _debate(service)
    _run(stances.save_before(debate, SAM, _before("against"), TODAY))
    saved = _run(stances.save_after(debate, SAM, _after("for", "Off-topic advert."), TODAY))
    _run(stances.moderate_note(str(saved["_id"]), AdminStanceUpdate(status="hidden")))
    _run(stances.save_after(debate, SAM, _after("for", "Edited to sneak back."), TODAY))
    results = _run(stances.results(debate.id))
    assert results["notes"] == [] and results["towards_for"] == 1
    assert [n["note"] for n in _run(stances.all_notes(debate.id))] == ["Edited to sneak back."]


def test_results_stay_hidden_from_the_page_while_the_debate_is_open(monkeypatch):
    from app.services import debate_page_service

    service = _service()
    debate = _debate(service, closes_on="2999-01-01")
    monkeypatch.setattr(debate_page_service, "get_database", lambda: service.database)
    monkeypatch.setattr(debate_page_service, "get_rooms", lambda db: _no_rooms())
    context = _run(debate_page_service.get_debate_context(slug=debate.slug, member=None))
    assert context["results"] is None

    _run(service.update_debate(debate.id, DebateInput(motion=debate.motion, closes_on="2000-01-01", status="published")))
    context = _run(debate_page_service.get_debate_context(slug=debate.slug, member=None))
    assert context["results"]["changed"] == 0


async def _no_rooms():
    return []


def test_deleting_a_debate_removes_its_stances():
    service = _service()
    debate = _debate(service)
    _run(_stances(service).save_before(debate, SAM, _before("for"), TODAY))
    _run(service.delete_debate(debate.id))
    assert service.stances.documents == []


@pytest.mark.parametrize("attack", ["<script>alert(1)</script>", "[x](javascript:alert(1))", "<img src=x onerror=alert(1)>"])
def test_note_html_is_never_rendered(attack):
    service = _service()
    stances = _stances(service)
    debate = _debate(service)
    _run(stances.save_after(debate, SAM, _after("for", "Convinced. " + attack), TODAY))
    note = results_view(_run(stances.results(debate.id)))["notes"][0]
    html = str(note["note_html"])
    assert "<script" not in html and "<img" not in html and 'href="javascript' not in html


# --- page design helpers --------------------------------------------------------

def test_this_house_believes_becomes_a_label_above_the_motion():
    from app.services.debate_page_service import split_motion

    assert split_motion("This house believes remote work is better") == ("This house believes", "remote work is better")
    assert split_motion("this house believes, that cats rule") == ("This house believes", "that cats rule")
    assert split_motion("Should cities ban cars?") == (None, "Should cities ban cars?")
    assert split_motion("This house believes") == (None, "This house believes")  # nothing after it


def test_time_left_counts_days_including_the_last():
    from app.services.debate_page_service import time_left

    assert time_left("2026-11-01", "2026-10-18") == "14 days left"
    assert time_left("2026-10-19", "2026-10-18") == "1 day left"
    assert time_left("2026-10-18", "2026-10-18") == "Last day"


def test_result_bars_run_for_undecided_against_and_add_up_to_100():
    service = _service()
    stances = _stances(service)
    debate = _debate(service)
    for member, stance in zip([_member(n) for n in range(1, 5)], ("for", "for", "against", "undecided")):
        _run(stances.save_after(debate, member, _after(stance), TODAY))
    results = results_view(_run(stances.results(debate.id)))
    bar = results["after_bar"]
    assert [s["stance"] for s in bar] == ["for", "undecided", "against"]
    assert [(s["x"], s["width"]) for s in bar] == [(0, 50.0), (50.0, 25.0), (75.0, 25.0)]
    assert results["compared"] == 0  # nobody gave a "before"


def test_side_rebuttal_and_stance_counts_cover_only_visible_items():
    service = _service()
    debate, argument = _debate_with_argument(service)
    hidden = _run(service.save_argument(debate, SAM, _argue("against"), TODAY))
    _run(service.moderate_argument(hidden.id, AdminArgumentUpdate(status="hidden")))
    _run(service.save_rebuttal(debate, argument.id, LEE, REPLY, TODAY))
    _run(_stances(service).save_before(debate, LEE, _before("for"), TODAY))
    assert _run(service.side_counts([debate.id])) == {debate.id: {"for": 1, "against": 0}}
    assert _run(service.rebuttal_counts([debate.id])) == {debate.id: 1}
    assert _run(_stances(service).stance_counts([debate.id])) == {debate.id: 1}


def test_long_cases_fold_behind_a_preview():
    service = _service()
    debate = _debate(service)
    short = _argument_view(_run(service.save_argument(debate, MIRA, _argue(), TODAY)))
    long_body = "A sentence that makes one careful point about commuting. " * 10
    long = _argument_view(_run(service.save_argument(debate, SAM, _argue(body=long_body), TODAY)))
    assert short["is_long"] is False and short["initial"] == "M"
    assert long["is_long"] is True and long["preview"].endswith("…") and len(long["preview"]) <= 280
