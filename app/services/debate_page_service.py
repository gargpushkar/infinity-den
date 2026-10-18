from datetime import date, datetime
from typing import Any

from app.config.constants import DEBATE_SIDE_LABELS, RATING_DIMENSIONS, RATINGS_NEEDED, REBUTTALS_SHOWN, STANCE_LABELS
from app.database.mongodb import get_database
from app.schemas.debate import ArgumentRead, DebateRead, RebuttalRead
from app.schemas.user import MemberRead
from app.services.article_page_service import room_url
from app.services.debate_rating_service import DebateRatingService
from app.services.debate_service import DebateService, is_open
from app.services.debate_stance_service import DebateStanceService
from app.services.member_article_service import sources_text
from app.services.nav_service import get_rooms
from app.services.question_service import site_today
from app.utils.covers import cover_url
from app.utils.markdown import plain_text, render_markdown


MOTION_OPENING = "This house believes"
BAR_ORDER = ("for", "undecided", "against")  # results bars run warm to cool
PREVIEW_LENGTH = 280


def debate_url(slug: str) -> str:
    return f"/debates/{slug}"


async def get_debates_context() -> dict[str, Any]:
    """Every published debate: open ones closing soonest first, then the archive,
    each closed one with how minds moved."""
    db = get_database()
    service = DebateService(database=db)
    stances = DebateStanceService(database=db)
    today = site_today()
    debates = await service.published_debates()
    stats = await _stats(service, stances, [d.id for d in debates])
    views = [_debate_view(d, today, stats) for d in debates]
    for view in views:
        if not view["is_open"]:
            # ponytail: one results query per past debate; fine for a few hundred.
            view["results"] = results_view(await stances.results(view["id"]))
    return {
        "open_debates": [v for v in reversed(views) if v["is_open"]],
        "closed_debates": [v for v in views if not v["is_open"]],
    }


async def _stats(service: DebateService, stances: DebateStanceService, debate_ids: list[str]) -> dict[str, dict]:
    return {
        "sides": await service.side_counts(debate_ids),
        "rebuttals": await service.rebuttal_counts(debate_ids),
        "stances": await stances.stance_counts(debate_ids),
    }


async def get_debate_context(*, slug: str, member: MemberRead | None) -> dict[str, Any] | None:
    """One published debate with its arguments by side. None if there is no such debate."""
    db = get_database()
    service = DebateService(database=db)
    debate = await service.get_published_debate(slug)
    if debate is None:
        return None

    today = site_today()
    arguments = await service.public_arguments(debate.id)
    own = await service.member_argument(debate.id, member) if member else None
    threads = await service.public_rebuttals(debate.id)
    own_rebuttals = await service.member_rebuttals(debate.id, member) if member else {}
    ratings = DebateRatingService(database=db)
    averages = await ratings.averages(debate.id)
    own_ratings = await ratings.member_ratings(debate.id, member) if member else {}
    debate_open = is_open(debate, today)
    stances = DebateStanceService(database=db)
    own_stance = await stances.member_stance(debate.id, member) if member else None
    rooms = {room["slug"]: room for room in await get_rooms(db)}
    room = rooms.get(debate.category_id or "")
    views = [
        _with_rating(
            _with_thread(_argument_view(a), threads.get(a.id, []), own_rebuttals.get(a.id)),
            averages.get(a.id), own_ratings.get(a.id), debate_open=debate_open,
        )
        for a in arguments
    ]

    stats = await _stats(service, stances, [debate.id])
    return {
        "debate": _debate_view(debate, today, stats),
        "room": {"name": room["name"], "url": room_url(room["slug"])} if room else None,
        "sides": [
            {"value": side, "label": label, "arguments": [v for v in views if v["side"] == side]}
            for side, label in DEBATE_SIDE_LABELS.items()
        ],
        "own_argument": _argument_view(own) if own else None,
        "side_labels": DEBATE_SIDE_LABELS,
        "rating_dimensions": RATING_DIMENSIONS,
        "ratings_needed": RATINGS_NEEDED,
        "stance_labels": STANCE_LABELS,
        "own_stance": _own_stance_view(own_stance),
        # Results stay hidden while the debate is open, so they can't sway anyone.
        "results": None if debate_open else results_view(await stances.results(debate.id)),
    }


def results_view(results: dict[str, Any]) -> dict[str, Any]:
    return {
        **results,
        "before_bar": _bar(results["before"]),
        "after_bar": _bar(results["after"]),
        "notes": [_note_view(stance) for stance in results["notes"]],
    }


def _bar(split: dict[str, Any]) -> list[dict[str, Any]]:
    """Segments of a 0-100 bar, For to Against, for an inline SVG (no style attributes)."""
    rows = {row["stance"]: row for row in split["rows"]}
    segments, x = [], 0.0
    for stance in BAR_ORDER:
        row = rows[stance]
        width = 100 * row["count"] / split["total"] if split["total"] else 0
        segments.append({**row, "x": round(x, 2), "width": round(width, 2)})
        x += width
    return segments


def _own_stance_view(stance: dict[str, Any] | None) -> dict[str, Any] | None:
    if stance is None:
        return None
    return {
        "before": stance.get("before"),
        "before_label": STANCE_LABELS.get(stance.get("before") or ""),
        "after": stance.get("after"),
        "after_label": STANCE_LABELS.get(stance.get("after") or ""),
        "note": stance.get("note") or "",
        "note_hidden": bool(stance.get("note")) and stance.get("status") == "hidden",
    }


def _note_view(stance: dict[str, Any]) -> dict[str, Any]:
    before, after = stance.get("before"), stance["after"]
    return {
        "id": str(stance["_id"]),
        "author": stance["author"],
        "author_url": f"/members/{stance['author_username']}",
        "author_username": stance["author_username"],
        "before_label": STANCE_LABELS.get(before or ""),
        "after_label": STANCE_LABELS[after],
        "changed": bool(before) and before != after,
        "note_html": render_markdown(stance["note"]),
    }


def own_argument_values(context: dict[str, Any]) -> dict[str, Any]:
    """Prefill the argument form with the member's existing argument."""
    own = context.get("own_argument")
    if not own:
        return {}
    return {"side": own["side"], "claim": own["claim"], "body": own["body"], "sources": own["sources_text"]}


def _day_label(moment: datetime) -> str:
    return f"{moment:%b} {moment.day}, {moment:%Y}"


def _date_label(value: str) -> str:
    day = date.fromisoformat(value)
    return f"{day:%B} {day.day}, {day:%Y}"


def _debate_view(debate: DebateRead, today: str, stats: dict[str, dict]) -> dict[str, Any]:
    sides = stats["sides"].get(debate.id, dict.fromkeys(DEBATE_SIDE_LABELS, 0))
    total = sum(sides.values())
    kicker, rest = split_motion(debate.motion)
    return {
        "id": debate.id,
        "motion": debate.motion,
        "motion_kicker": kicker,
        "motion_rest": rest,
        "intro": debate.intro,
        "slug": debate.slug,
        "url": debate_url(debate.slug),
        "cover_url": cover_url("debate", debate.slug),
        "is_open": is_open(debate, today),
        "closes_label": _date_label(debate.closes_on),
        "time_left": time_left(debate.closes_on, today),
        "argument_count": total,
        "side_counts": sides,
        "for_percent": round(100 * sides["for"] / total) if total else 50,
        "rebuttal_count": stats["rebuttals"].get(debate.id, 0),
        "stance_count": stats["stances"].get(debate.id, 0),
    }


def split_motion(motion: str) -> tuple[str | None, str]:
    """"This house believes X" shows the opening as a small label above X."""
    if motion.lower().startswith(MOTION_OPENING.lower()):
        rest = motion[len(MOTION_OPENING):].lstrip(" ,:")
        if rest:
            return MOTION_OPENING, rest
    return None, motion


def time_left(closes_on: str, today: str) -> str:
    days = (date.fromisoformat(closes_on) - date.fromisoformat(today)).days
    if days <= 0:
        return "Last day"
    return "1 day left" if days == 1 else f"{days} days left"


def _with_thread(view: dict[str, Any], rebuttals: list[RebuttalRead], own: RebuttalRead | None) -> dict[str, Any]:
    """Attach an argument's rebuttals: the first few shown, the rest folded.

    The member's own rebuttal is always in the thread, even when editors hid it.
    """
    thread = [_rebuttal_view(r) for r in rebuttals]
    if own is not None and own.status == "hidden":
        thread.append(_rebuttal_view(own))
    own_view = next((r for r in thread if own is not None and r["id"] == own.id), None)
    return {
        **view,
        "rebuttal_count": len(rebuttals),
        "rebuttals_shown": thread[:REBUTTALS_SHOWN],
        "rebuttals_folded": thread[REBUTTALS_SHOWN:],
        "own_rebuttal": own_view,
        "own_rebuttal_folded": own_view is not None and own_view in thread[REBUTTALS_SHOWN:],
    }


def _with_rating(
    view: dict[str, Any], average: dict[str, Any] | None, own: dict[str, int] | None, *, debate_open: bool
) -> dict[str, Any]:
    """Averages show once enough members have rated, and then only to members
    who rated it themselves, or to everyone after the debate closes."""
    enough = average is not None and average["count"] >= RATINGS_NEEDED
    return {
        **view,
        "rating": average if enough and (own is not None or not debate_open) else None,
        "own_rating": own,
    }


def _rebuttal_view(rebuttal: RebuttalRead) -> dict[str, Any]:
    return {
        "id": rebuttal.id,
        "author": rebuttal.author,
        "author_url": f"/members/{rebuttal.author_username}",
        "author_username": rebuttal.author_username,
        "body": rebuttal.body,
        "body_html": render_markdown(rebuttal.body),
        "is_hidden": rebuttal.status == "hidden",
        "date_label": _day_label(rebuttal.created_at),
        "edited_label": _day_label(rebuttal.edited_at) if rebuttal.edited_at else None,
    }


def _argument_view(argument: ArgumentRead) -> dict[str, Any]:
    return {
        "id": argument.id,
        "author": argument.author,
        "author_url": f"/members/{argument.author_username}",
        "author_username": argument.author_username,
        "side": argument.side,
        "side_label": DEBATE_SIDE_LABELS[argument.side],
        "claim": argument.claim,
        "initial": (argument.author[:1] or "?").upper(),
        "body": argument.body,
        "body_html": render_markdown(argument.body),
        # Long cases show an opening and fold the rest behind "Read the full case".
        "preview": plain_text(argument.body, PREVIEW_LENGTH),
        "is_long": len(plain_text(argument.body, 100_000)) > PREVIEW_LENGTH,
        "sources": [source.model_dump() for source in argument.sources],
        "sources_text": sources_text(argument.sources),
        "is_featured": argument.is_featured,
        "is_hidden": argument.status == "hidden",
        "date_label": _day_label(argument.created_at),
        "edited_label": _day_label(argument.edited_at) if argument.edited_at else None,
    }
