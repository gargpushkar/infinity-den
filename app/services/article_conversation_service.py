"""The member side of an article page: its comments and whether the reader saved it."""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.schemas.comment import CommentRead
from app.schemas.user import MemberRead
from app.services.bookmark_service import BookmarkService
from app.services.comment_service import CommentService
from app.utils.markdown import render_markdown


async def published_article_id(slug: str, database: AsyncIOMotorDatabase | None = None) -> str | None:
    db = database if database is not None else get_database()
    document = await db[ARTICLE_COLLECTION].find_one({"slug": slug, "status": ARTICLE_STATUS_PUBLISHED}, {"_id": 1})
    return str(document["_id"]) if document else None


async def get_conversation_context(
    article_id: str,
    member: MemberRead | None,
    database: AsyncIOMotorDatabase | None = None,
) -> dict[str, Any]:
    try:
        db = database if database is not None else get_database()
        comments = await CommentService(database=db).for_article(article_id, member)
        is_saved = await BookmarkService(database=db).is_saved(member, article_id) if member else False
    except (RuntimeError, PyMongoError):
        comments, is_saved = [], False
    views = [comment_view(comment, member) for comment in comments]
    return {
        "comments": views,
        "comment_count": sum(not view["is_hidden"] for view in views),
        "is_saved": is_saved,
    }


def comment_view(comment: CommentRead, member: MemberRead | None) -> dict[str, Any]:
    return {
        "id": comment.id,
        "author": comment.author,
        "author_url": f"/members/{comment.author_username}",
        # render_markdown escapes first and only links http(s); never member HTML.
        "body_html": render_markdown(comment.body),
        "date_label": f"{comment.created_at:%b} {comment.created_at.day}, {comment.created_at:%Y}",
        "is_own": bool(member and member.id == comment.user_id),
        "is_hidden": comment.status == "hidden",
    }
