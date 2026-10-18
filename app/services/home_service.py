"""The homepage, in the section order of vision.md -> HOMEPAGE.

Each section hides itself when it has nothing to show; an empty section reads
as broken rather than as one waiting to be filled.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_FORMAT_EXPERIENCE, ARTICLE_STATUS_PUBLISHED, RESPONSE_KIND_LABELS
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.schemas.article import ArticleRead
from app.services.article_page_service import article_to_card_context
from app.services.debate_page_service import debate_url
from app.services.debate_service import DebateService, is_open
from app.services.nav_service import fallback_rooms, get_rooms
from app.services.play_page_service import claim_context
from app.services.question_page_service import question_url
from app.services.question_service import QuestionService, site_today
from app.services.quiz_service import QuizService


SECTION_LIMIT = 3
PUBLISHED = {"status": ARTICLE_STATUS_PUBLISHED}
NEWEST = [("published_at", DESCENDING), ("created_at", DESCENDING)]


async def get_homepage_context(
    *,
    claim_slug: str | None = None,
    answer: str = "",
    after: str | None = None,
    database: Any = None,
) -> dict[str, Any]:
    """`claim_slug` and `answer` show an answered claim in place; `after` skips the one just played."""
    try:
        db = database if database is not None else get_database()
        rooms = await get_rooms(db) or fallback_rooms()
        room_names = {room["slug"]: room["name"] for room in rooms}
        shown: set[str] = set()

        async def reading_sections() -> tuple[list, list, list]:
            # In order, because each section skips what an earlier one showed.
            experiences = await _pieces(
                db, {**PUBLISHED, "article_format": ARTICLE_FORMAT_EXPERIENCE},
                [("is_featured", DESCENDING), *NEWEST], room_names, shown,
            )
            ideas = await _pieces(db, {**PUBLISHED, "is_editors_pick": True}, NEWEST, room_names, shown)
            community = await _pieces(db, {**PUBLISHED, "author_id": {"$ne": None}}, NEWEST, room_names, shown)
            return experiences, ideas, community

        # The question, the debate, the Arcade, and the reading sections don't depend on each other.
        question, debate, arcade, (experiences, ideas, community) = await asyncio.gather(
            _todays_question(db, room_names),
            _featured_debate(db),
            _arcade(db, claim_slug=claim_slug, answer=answer, after=after),
            reading_sections(),
        )
        return {
            "question": question,
            "debate": debate,
            "experiences": experiences,
            "arcade": arcade,
            "rooms": rooms,
            "ideas": ideas,
            "community": community,
        }
    except (RuntimeError, PyMongoError):
        return _fallback_context()


async def _pieces(
    db: Any,
    query: dict[str, Any],
    sort: list[tuple[str, int]],
    room_names: dict[str, str],
    shown: set[str],
) -> list[dict[str, Any]]:
    """Up to three cards, skipping pieces an earlier section already showed."""
    cursor = db[ARTICLE_COLLECTION].find({**query, "slug": {"$nin": list(shown)}}).sort(sort).limit(SECTION_LIMIT)
    cards = [article_to_card_context(ArticleRead.model_validate(document), room_names) async for document in cursor]
    shown.update(card["slug"] for card in cards)
    return cards


async def _todays_question(db: Any, room_names: dict[str, str]) -> dict[str, Any] | None:
    service = QuestionService(database=db)
    question = await service.current_question(site_today())
    if question is None:
        return None
    responses = await service.public_responses(question.id)
    featured = next((response for response in responses if response.is_featured), None)
    return {
        "text": question.text,
        "intro": question.intro,
        "url": question_url(question.slug),
        "room": room_names.get(question.category_id or ""),
        "response_count": len(responses),
        "featured": (
            {"body": _plain(featured.body), "author": featured.author, "kind_label": RESPONSE_KIND_LABELS.get(featured.kind, "")}
            if featured
            else None
        ),
    }


async def _featured_debate(db: Any) -> dict[str, Any] | None:
    """The open debate closing soonest; with none open, the one that closed last."""
    service = DebateService(database=db)
    today = site_today()
    debates = await service.published_debates()  # latest closing date first
    open_debates = [d for d in debates if is_open(d, today)]
    debate = open_debates[-1] if open_debates else next(iter(debates), None)
    if debate is None:
        return None
    counts = await service.argument_counts([debate.id])
    return {
        "motion": debate.motion,
        "url": debate_url(debate.slug),
        "is_open": bool(open_debates),
        "argument_count": counts.get(debate.id, 0),
    }


async def _arcade(db: Any, *, claim_slug: str | None, answer: str, after: str | None) -> dict[str, Any] | None:
    service = QuizService(database=db)
    item = await service.get_published(claim_slug) if claim_slug else None
    if item is None:
        item = await service.random_published(exclude_slug=after)
        answer = ""  # an unknown or drafted claim never reveals anything
    if item is None:
        return None
    return (await claim_context(service, item, answer=answer, on_home=True))["claim"]


def _plain(markdown: str, limit: int = 220) -> str:
    """A response's opening as plain text; the Jinja template escapes it."""
    text = re.sub(r"(?m)^\s*(?:[#>]+|-)\s*", "", markdown)  # headings, quotes, list marks
    text = " ".join(re.sub(r"\[([^\]]*)\]\([^)]*\)|[*_`]", r"\1", text).split())  # links, emphasis
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "\u2026"


def _fallback_context() -> dict[str, Any]:
    """Rendered when MongoDB is unreachable, so the homepage still stands up."""
    return {"question": None, "debate": None, "experiences": [], "arcade": None, "rooms": fallback_rooms(), "ideas": [], "community": []}
