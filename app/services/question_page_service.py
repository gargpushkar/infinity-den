from datetime import date
from typing import Any

from app.config.constants import RESPONSE_KIND_LABELS
from app.database.mongodb import get_database
from app.schemas.question import QuestionRead, ResponseRead
from app.schemas.user import MemberRead
from app.services.article_page_service import room_url
from app.services.member_article_service import sources_text
from app.services.nav_service import get_rooms
from app.services.question_service import QuestionService, site_today
from app.utils.markdown import render_markdown


def question_url(slug: str) -> str:
    return f"/questions/{slug}"


async def get_question_room_context(
    *,
    slug: str | None,
    member: MemberRead | None,
) -> dict[str, Any] | None:
    """Today's (or the latest) question, or a specific past one by slug.

    Returns None when a slug is given but no live question has it.
    """
    db = get_database()
    service = QuestionService(database=db)
    today = site_today()

    question = await service.get_live_question(slug, today) if slug else await service.current_question(today)
    if question is None:
        if slug:
            return None
        return {"question": None, "past_questions": [], "today": today}

    responses = await service.public_responses(question.id)
    own = await service.member_response(question.id, member) if member else None
    past = await service.past_questions(today, exclude_id=question.id)
    counts = await service.response_counts([question.id, *(q.id for q in past)])
    rooms = {room["slug"]: room for room in await get_rooms(db)}
    room = rooms.get(question.category_id or "")

    return {
        "question": _question_view(question, today, counts),
        "room": {"name": room["name"], "url": room_url(room["slug"])} if room else None,
        "featured_responses": [_response_view(r) for r in responses if r.is_featured],
        "responses": [_response_view(r) for r in responses if not r.is_featured],
        "own_response": _response_view(own) if own else None,
        "past_questions": [_question_view(q, today, counts) for q in past],
        "kinds": RESPONSE_KIND_LABELS,
        "today": today,
    }


def own_response_values(context: dict[str, Any]) -> dict[str, Any]:
    """Prefill the response form with the member's existing response."""
    own = context.get("own_response")
    if not own:
        return {"kind": "answer"}
    return {"kind": own["kind"], "body": own["body"], "sources": own["sources_text"]}


def _question_view(question: QuestionRead, today: str, counts: dict[str, int]) -> dict[str, Any]:
    published = date.fromisoformat(question.publish_date)
    return {
        "id": question.id,
        "text": question.text,
        "intro": question.intro,
        "slug": question.slug,
        "url": question_url(question.slug),
        "is_today": question.publish_date == today,
        "date_label": f"{published:%B} {published.day}, {published:%Y}",
        "response_count": counts.get(question.id, 0),
    }


def _response_view(response: ResponseRead) -> dict[str, Any]:
    return {
        "id": response.id,
        "author": response.author,
        "author_url": f"/members/{response.author_username}",
        "kind": response.kind,
        "kind_label": RESPONSE_KIND_LABELS.get(response.kind, ""),
        "body": response.body,
        "body_html": render_markdown(response.body),
        "sources": [source.model_dump() for source in response.sources],
        "sources_text": sources_text(response.sources),
        "is_featured": response.is_featured,
        "is_hidden": response.status == "hidden",
        "date_label": f"{response.created_at:%b} {response.created_at.day}, {response.created_at:%Y}",
    }
