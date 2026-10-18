from typing import Any

from pymongo.errors import PyMongoError

from app.config.constants import (
    ARTICLE_STATUS_PUBLISHED,
    DEBATE_SIDE_LABELS,
    RATING_DIMENSIONS,
    RATINGS_NEEDED,
    RESPONSE_KIND_LABELS,
)
from app.database.mongodb import get_database
from app.schemas.article import ArticleQueryParams
from app.schemas.debate import ArgumentRead, DebateRead
from app.schemas.user import MemberPublic, MemberRead
from app.services.article_page_service import article_to_card_context
from app.services.article_service import ArticleService
from app.services.debate_page_service import debate_url
from app.services.debate_rating_service import DebateRatingService
from app.services.debate_service import DebateService, is_open
from app.services.member_reputation_service import STRENGTH_GUIDE, earned_strengths, featured_and_researched
from app.services.nav_service import get_rooms
from app.services.question_service import QuestionService, site_today
from app.services.user_service import UserService
from app.utils.markdown import plain_text


PROFILE_PIECE_LIMIT = 24
PROFILE_SHOWN = 6  # responses and arguments beyond this fold behind "Show all"


def member_profile_url(username: str) -> str:
    return f"/members/{username}"


async def get_member_profile_context(username: str, viewer: MemberRead | None = None) -> dict[str, Any] | None:
    """A member's public profile: who they are, what they've earned, and their contributions.

    `viewer` is whoever is looking; their own profile adds the strengths guide.
    """
    try:
        db = get_database()
        member = await UserService(database=db).get_member_by_username(username)
        if member is None:
            return None

        pieces = await ArticleService(database=db).list_articles(
            ArticleQueryParams(per_page=PROFILE_PIECE_LIMIT, status=ARTICLE_STATUS_PUBLISHED, author_id=member.id)
        )
        room_lookup = {room["slug"]: room["name"] for room in await get_rooms(db)}
        responses = await QuestionService(database=db).member_public_responses(member.id)
        debates = DebateService(database=db)
        arguments = await debates.member_arguments(member.id)
        rebuttals = await debates.member_public_rebuttals(member.id)
        thoughtful = [r for r in rebuttals if r.is_featured]
        debate_lookup = await debates.published_debates_by_id(list({a.debate_id for a in arguments} | {r.debate_id for r in thoughtful}))
        rebutted = await debates.arguments_by_id([r.argument_id for r in thoughtful])
        averages = await DebateRatingService(database=db).averages_for([a.id for a in arguments])
        featured, researched, thoughtful_count = await featured_and_researched(db, member.id)
    except (RuntimeError, PyMongoError):
        return None

    today = site_today()
    arguments = [a for a in arguments if a.debate_id in debate_lookup]  # drafts and deleted debates stay out
    closed_averages = [
        averages[a.id] for a in arguments if a.id in averages and not is_open(debate_lookup[a.debate_id], today)
    ]
    response_views = [_response_view(item) for item in responses]
    argument_views = [_argument_view(a, debate_lookup[a.debate_id], averages.get(a.id), today) for a in arguments]

    return {
        "member": {**public_profile(member), "initial": (member.display_name[:1] or "?").upper(), "tone": _tone(member.username)},
        "is_own": viewer is not None and viewer.id == member.id,
        "strengths": earned_strengths(
            rated_arguments=closed_averages, researched_pieces=researched,
            featured=featured, thoughtful_rebuttals=thoughtful_count,
        ),
        "strength_guide": STRENGTH_GUIDE,
        "counts": {"pieces": pieces.total, "responses": len(responses), "arguments": len(arguments), "rebuttals": len(rebuttals)},
        "pieces": [article_to_card_context(piece, room_lookup) for piece in pieces.items],
        "piece_count": pieces.total,
        "responses_shown": response_views[:PROFILE_SHOWN],
        "responses_folded": response_views[PROFILE_SHOWN:],
        "arguments_shown": argument_views[:PROFILE_SHOWN],
        "arguments_folded": argument_views[PROFILE_SHOWN:],
        "thoughtful_rebuttals": [
            {
                "body": plain_text(r.body, 280),
                "url": f"{debate_url(debate_lookup[r.debate_id].slug)}#rebuttal-{r.id}",
                "argument_claim": rebutted[r.argument_id].claim,
                "argument_author": rebutted[r.argument_id].author,
            }
            for r in thoughtful
            if r.debate_id in debate_lookup and r.argument_id in rebutted
        ],
        "rating_dimensions": RATING_DIMENSIONS,
    }


def _tone(username: str) -> str:
    """The initial square's colour, from the username: warm or cool, so profiles vary without photos."""
    return "against" if sum(username.encode()) % 2 else "for"


def _response_view(item: dict[str, Any]) -> dict[str, Any]:
    response, question = item["response"], item["question"]
    return {
        "question": question.text,
        "url": f"/questions/{question.slug}#response-{response.id}",
        "kind": response.kind,
        "kind_label": RESPONSE_KIND_LABELS.get(response.kind, ""),
        "is_featured": response.is_featured,
        "date_label": f"{response.created_at:%b} {response.created_at.day}",
        "excerpt": plain_text(response.body, 200),
    }


def _argument_view(argument: ArgumentRead, debate: DebateRead, average: dict[str, Any] | None, today: str) -> dict[str, Any]:
    closed = not is_open(debate, today)
    return {
        "side": argument.side,
        "side_label": DEBATE_SIDE_LABELS[argument.side],
        "claim": argument.claim,
        "motion": debate.motion,
        "url": f"{debate_url(debate.slug)}#argument-{argument.id}",
        "is_featured": argument.is_featured,
        "is_open": not closed,
        # The debate page keeps averages blind until it closes; so does the profile.
        "rating": average if closed and average and average["count"] >= RATINGS_NEEDED else None,
    }


def public_profile(member: MemberRead) -> dict[str, Any]:
    """The only member fields a public page may render."""
    public = MemberPublic.model_validate(member, from_attributes=True)

    return {
        **public.model_dump(),
        "joined_label": f"{public.created_at:%B %Y}",
        "url": member_profile_url(public.username),
    }
