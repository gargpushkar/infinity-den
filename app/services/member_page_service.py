from typing import Any

from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.schemas.article import ArticleQueryParams
from app.schemas.user import MemberPublic, MemberRead
from app.services.article_page_service import article_to_card_context
from app.services.article_service import ArticleService
from app.services.nav_service import get_rooms
from app.services.question_service import QuestionService
from app.services.user_service import UserService


PROFILE_PIECE_LIMIT = 24


def member_profile_url(username: str) -> str:
    return f"/members/{username}"


async def get_member_profile_context(username: str) -> dict[str, Any] | None:
    try:
        db = get_database()
        member = await UserService(database=db).get_member_by_username(username)
        if member is None:
            return None

        pieces = await ArticleService(database=db).list_articles(
            ArticleQueryParams(
                per_page=PROFILE_PIECE_LIMIT,
                status=ARTICLE_STATUS_PUBLISHED,
                author_id=member.id,
            )
        )
        room_lookup = {room["slug"]: room["name"] for room in await get_rooms(db)}
        responses = await QuestionService(database=db).member_public_responses(member.id)
    except (RuntimeError, PyMongoError):
        return None

    return {
        "member": public_profile(member),
        "pieces": [article_to_card_context(piece, room_lookup) for piece in pieces.items],
        "piece_count": pieces.total,
        "responses": [
            {
                "question": item["question"].text,
                "url": f"/questions/{item['question'].slug}",
                "excerpt": item["response"].body[:220] + ("…" if len(item["response"].body) > 220 else ""),
            }
            for item in responses
        ],
    }


def public_profile(member: MemberRead) -> dict[str, Any]:
    """The only member fields a public page may render."""
    public = MemberPublic.model_validate(member, from_attributes=True)

    return {
        **public.model_dump(),
        "joined_label": f"{public.created_at:%B %Y}",
        "url": member_profile_url(public.username),
    }
