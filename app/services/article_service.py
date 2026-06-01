from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION, create_article_document
from app.schemas.article import (
    ArticleCreate,
    ArticleListResponse,
    ArticleQueryParams,
    ArticleRead,
    ArticleUpdate,
)


class ArticleServiceError(Exception):
    pass


class ArticleNotFoundError(ArticleServiceError):
    pass


class ArticleSlugConflictError(ArticleServiceError):
    pass


class ArticleService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database or get_database()

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.database[ARTICLE_COLLECTION]

    async def create_article(self, payload: ArticleCreate) -> ArticleRead:
        article_document = create_article_document(**payload.model_dump())

        try:
            result = await self.collection.insert_one(article_document.to_mongo())
        except DuplicateKeyError as exc:
            raise ArticleSlugConflictError(
                "An article with this slug already exists."
            ) from exc

        created_article = await self.collection.find_one({"_id": result.inserted_id})
        if created_article is None:
            raise ArticleNotFoundError("Created article could not be loaded.")

        return self._to_article_read(created_article)

    async def get_article_by_id(self, article_id: str) -> ArticleRead | None:
        object_id = self._to_object_id(article_id)
        if object_id is None:
            return None

        article = await self.collection.find_one({"_id": object_id})
        if article is None:
            return None

        return self._to_article_read(article)

    async def get_article_by_slug(self, slug: str) -> ArticleRead | None:
        article = await self.collection.find_one({"slug": slug.strip().lower()})
        if article is None:
            return None

        return self._to_article_read(article)

    async def list_articles(self, query: ArticleQueryParams) -> ArticleListResponse:
        article_filter = self._build_filter(query)
        sort_direction = ASCENDING if query.sort_direction == "asc" else DESCENDING
        skip = (query.page - 1) * query.per_page

        cursor = (
            self.collection.find(article_filter)
            .sort(query.sort_by, sort_direction)
            .skip(skip)
            .limit(query.per_page)
        )
        articles = [self._to_article_read(article) async for article in cursor]
        total = await self.collection.count_documents(article_filter)

        return ArticleListResponse(
            items=articles,
            total=total,
            page=query.page,
            per_page=query.per_page,
            total_pages=0,
        )

    async def update_article(self, article_id: str, payload: ArticleUpdate) -> ArticleRead:
        object_id = self._to_object_id(article_id)
        if object_id is None:
            raise ArticleNotFoundError("Article was not found.")

        update_data = payload.model_dump(exclude_unset=True)
        update_data["updated_at"] = self._utc_now()

        try:
            updated_article = await self.collection.find_one_and_update(
                {"_id": object_id},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            raise ArticleSlugConflictError(
                "An article with this slug already exists."
            ) from exc

        if updated_article is None:
            raise ArticleNotFoundError("Article was not found.")

        return self._to_article_read(updated_article)

    async def delete_article(self, article_id: str) -> bool:
        object_id = self._to_object_id(article_id)
        if object_id is None:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count == 1

    async def increment_article_views(self, article_id: str) -> ArticleRead:
        object_id = self._to_object_id(article_id)
        if object_id is None:
            raise ArticleNotFoundError("Article was not found.")

        updated_article = await self.collection.find_one_and_update(
            {"_id": object_id},
            {
                "$inc": {"views": 1},
                "$set": {"updated_at": self._utc_now()},
            },
            return_document=ReturnDocument.AFTER,
        )
        if updated_article is None:
            raise ArticleNotFoundError("Article was not found.")

        return self._to_article_read(updated_article)

    def _build_filter(self, query: ArticleQueryParams) -> dict[str, Any]:
        article_filter: dict[str, Any] = {}

        if query.status is not None:
            article_filter["status"] = query.status
        if query.category_id is not None:
            article_filter["category_id"] = query.category_id
        if query.tag is not None:
            article_filter["tags"] = query.tag
        if query.search is not None:
            article_filter["$text"] = {"$search": query.search}

        return article_filter

    def _to_article_read(self, article: dict[str, Any]) -> ArticleRead:
        return ArticleRead.model_validate(article)

    def _to_object_id(self, value: str) -> ObjectId | None:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)


def get_article_service(database: AsyncIOMotorDatabase | None = None) -> ArticleService:
    return ArticleService(database=database)
