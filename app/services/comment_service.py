"""Comments on published pieces. Flat, oldest first, posted immediately.

Editors hide comments (reports and moderation arrive with the reports branch);
a hidden comment stays visible to its author so they know what happened.
"""

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING

from app.database.mongodb import get_database
from app.models.comment import COMMENT_COLLECTION, CommentDocument
from app.schemas.comment import CommentInput, CommentRead
from app.schemas.user import MemberRead


# ponytail: one page of comments per piece; add paging if a piece ever passes this.
COMMENT_LIMIT = 200


def _object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


class CommentService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.comments = self.database[COMMENT_COLLECTION]

    async def for_article(self, article_id: str, member: MemberRead | None) -> list[CommentRead]:
        """Published comments, plus the member's own hidden ones, oldest first."""
        published = await self._find({"article_id": article_id, "status": "published"})
        own_hidden = (
            await self._find({"article_id": article_id, "status": "hidden", "user_id": member.id}) if member else []
        )
        return sorted([*published, *own_hidden], key=lambda comment: comment.created_at)

    async def add(self, article_id: str, member: MemberRead, payload: CommentInput) -> CommentRead:
        document = CommentDocument(
            article_id=article_id,
            user_id=member.id,
            author=member.display_name,
            author_username=member.username,
            body=payload.body,
        ).to_mongo()
        result = await self.comments.insert_one(document)
        return CommentRead.model_validate({**document, "_id": result.inserted_id})

    async def delete_own(self, comment_id: str, member: MemberRead) -> bool:
        result = await self.comments.delete_one({"_id": _object_id(comment_id), "user_id": member.id})
        return bool(result.deleted_count)

    async def _find(self, query: dict[str, Any]) -> list[CommentRead]:
        cursor = self.comments.find(query).sort([("created_at", ASCENDING)]).limit(COMMENT_LIMIT)
        return [CommentRead.model_validate(document) async for document in cursor]
