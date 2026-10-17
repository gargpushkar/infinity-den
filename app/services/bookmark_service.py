"""Bookmarks: pieces a member saved to read later, shown on /saved."""

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.bookmark import BOOKMARK_COLLECTION, BookmarkDocument
from app.schemas.article import ArticleRead
from app.schemas.user import MemberRead


SAVED_LIMIT = 200


class BookmarkService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.bookmarks = self.database[BOOKMARK_COLLECTION]

    async def is_saved(self, member: MemberRead, article_id: str) -> bool:
        return bool(await self.bookmarks.count_documents({"user_id": member.id, "article_id": article_id}, limit=1))

    async def save(self, member: MemberRead, article_id: str) -> None:
        try:
            await self.bookmarks.insert_one(BookmarkDocument(user_id=member.id, article_id=article_id).to_mongo())
        except DuplicateKeyError:
            pass  # already saved; the unique index makes a double click harmless

    async def remove(self, member: MemberRead, article_id: str) -> None:
        await self.bookmarks.delete_one({"user_id": member.id, "article_id": article_id})

    async def saved_articles(self, member: MemberRead) -> list[ArticleRead]:
        """Newest saved first. Pieces that are no longer published drop off quietly."""
        cursor = self.bookmarks.find({"user_id": member.id}).sort([("created_at", DESCENDING)]).limit(SAVED_LIMIT)
        order = [bookmark["article_id"] async for bookmark in cursor]
        ids = [object_id for object_id in map(_object_id, order) if object_id is not None]
        articles = {
            str(document["_id"]): ArticleRead.model_validate(document)
            async for document in self.database[ARTICLE_COLLECTION].find(
                {"_id": {"$in": ids}, "status": ARTICLE_STATUS_PUBLISHED}
            )
        }
        return [articles[article_id] for article_id in order if article_id in articles]


def _object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None
