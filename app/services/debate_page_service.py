from datetime import date
from typing import Any

from app.config.constants import DEBATE_SIDE_LABELS
from app.database.mongodb import get_database
from app.schemas.debate import ArgumentRead, DebateRead
from app.schemas.user import MemberRead
from app.services.article_page_service import room_url
from app.services.debate_service import DebateService, is_open
from app.services.member_article_service import sources_text
from app.services.nav_service import get_rooms
from app.services.question_service import site_today
from app.utils.markdown import render_markdown


def debate_url(slug: str) -> str:
    return f"/debates/{slug}"


async def get_debates_context() -> dict[str, Any]:
    """Every published debate: open ones closing soonest first, then the archive."""
    service = DebateService(database=get_database())
    today = site_today()
    debates = await service.published_debates()
    counts = await service.argument_counts([d.id for d in debates])
    views = [_debate_view(d, today, counts) for d in debates]
    return {
        "open_debates": [v for v in reversed(views) if v["is_open"]],
        "closed_debates": [v for v in views if not v["is_open"]],
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
    rooms = {room["slug"]: room for room in await get_rooms(db)}
    room = rooms.get(debate.category_id or "")
    views = [_argument_view(a) for a in arguments]

    return {
        "debate": _debate_view(debate, today, {debate.id: len(views)}),
        "room": {"name": room["name"], "url": room_url(room["slug"])} if room else None,
        "sides": [
            {"value": side, "label": label, "arguments": [v for v in views if v["side"] == side]}
            for side, label in DEBATE_SIDE_LABELS.items()
        ],
        "own_argument": _argument_view(own) if own else None,
        "side_labels": DEBATE_SIDE_LABELS,
    }


def own_argument_values(context: dict[str, Any]) -> dict[str, Any]:
    """Prefill the argument form with the member's existing argument."""
    own = context.get("own_argument")
    if not own:
        return {}
    return {"side": own["side"], "claim": own["claim"], "body": own["body"], "sources": own["sources_text"]}


def _date_label(value: str) -> str:
    day = date.fromisoformat(value)
    return f"{day:%B} {day.day}, {day:%Y}"


def _debate_view(debate: DebateRead, today: str, counts: dict[str, int]) -> dict[str, Any]:
    return {
        "id": debate.id,
        "motion": debate.motion,
        "intro": debate.intro,
        "slug": debate.slug,
        "url": debate_url(debate.slug),
        "is_open": is_open(debate, today),
        "closes_label": _date_label(debate.closes_on),
        "argument_count": counts.get(debate.id, 0),
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
        "body": argument.body,
        "body_html": render_markdown(argument.body),
        "sources": [source.model_dump() for source in argument.sources],
        "sources_text": sources_text(argument.sources),
        "is_featured": argument.is_featured,
        "is_hidden": argument.status == "hidden",
        "date_label": f"{argument.created_at:%b} {argument.created_at.day}, {argument.created_at:%Y}",
    }
