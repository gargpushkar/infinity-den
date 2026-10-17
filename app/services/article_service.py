from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import (
    ARTICLE_COLLECTION,
    create_article_document,
    missing_required_sources,
)
from app.schemas.article import (
    ArticleCreate,
    ArticleListResponse,
    ArticleQueryParams,
    ArticleRead,
    ArticleUpdate,
)
from app.services.cover_upload_service import discard_unused_cover
from app.services.tag_service import register_tags


class ArticleServiceError(Exception):
    pass


class ArticleNotFoundError(ArticleServiceError):
    pass


class ArticleSlugConflictError(ArticleServiceError):
    pass


class ArticleSourcesRequiredError(ArticleServiceError):
    pass


SOURCES_REQUIRED_MESSAGE = "Researched articles need at least one source before publishing."


class ArticleService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.database[ARTICLE_COLLECTION]

    async def create_article(self, payload: ArticleCreate) -> ArticleRead:
        if missing_required_sources(
            article_format=payload.article_format,
            status=payload.status,
            sources=payload.sources,
        ):
            raise ArticleSourcesRequiredError(SOURCES_REQUIRED_MESSAGE)

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

        return await self._published_tags_registered(self._to_article_read(created_article))

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

    async def get_article_detail(self, identifier: str) -> ArticleRead | None:
        clean_identifier = identifier.strip().lower()

        article = await self.get_article_by_id(clean_identifier)
        if article is not None:
            return article

        return await self.get_article_by_slug(clean_identifier)

    async def list_articles(self, query: ArticleQueryParams) -> ArticleListResponse:
        article_filter = self._build_filter(query)
        skip = (query.page - 1) * query.per_page

        cursor = (
            self.collection.find(article_filter)
            .sort(self._build_sort(query))
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
            sort_by=query.sort_by,
            sort_direction=query.sort_direction,
        )

    async def update_article(self, article_id: str, payload: ArticleUpdate) -> ArticleRead:
        object_id = self._to_object_id(article_id)
        if object_id is None:
            raise ArticleNotFoundError("Article was not found.")

        update_data = payload.model_dump(exclude_unset=True)

        # A partial update (such as the admin "publish" action) can make an
        # article live without touching its sources, so check the article as
        # it will be after this update. Updates that leave status, format, and
        # sources alone (featuring, retitling) are never blocked.
        if {"status", "article_format", "sources"} & update_data.keys():
            current = await self.collection.find_one(
                {"_id": object_id},
                {"article_format": 1, "status": 1, "sources": 1},
            )
            if current is None:
                raise ArticleNotFoundError("Article was not found.")
            merged = {**current, **update_data}
            if missing_required_sources(
                article_format=merged.get("article_format", ""),
                status=merged.get("status", ""),
                sources=merged.get("sources"),
            ):
                raise ArticleSourcesRequiredError(SOURCES_REQUIRED_MESSAGE)

        old_cover = None
        if {"cover_image", "correction_note"} & update_data.keys():
            current = await self.collection.find_one({"_id": object_id}, {"cover_image": 1, "correction_note": 1}) or {}
            old_cover = current.get("cover_image")
            if update_data.get("correction_note", current.get("correction_note")) != current.get("correction_note"):
                update_data["corrected_at"] = self._utc_now() if update_data["correction_note"] else None

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

        if old_cover != updated_article.get("cover_image"):
            await discard_unused_cover(self.database, old_cover)
        return await self._published_tags_registered(self._to_article_read(updated_article))

    async def _published_tags_registered(self, article: ArticleRead) -> ArticleRead:
        # Only published pieces add tags, so drafts never put filters on public pages.
        # Member pieces are published through update_article, so this covers them too.
        if article.status == ARTICLE_STATUS_PUBLISHED and article.tags:
            await register_tags(self.database, article.tags)
        return article

    async def delete_article(self, article_id: str) -> bool:
        object_id = self._to_object_id(article_id)
        if object_id is None:
            return False

        deleted = await self.collection.find_one_and_delete({"_id": object_id}, {"cover_image": 1})
        if deleted is None:
            return False
        await discard_unused_cover(self.database, deleted.get("cover_image"))
        return True

    async def increment_article_views(self, article_id: str) -> ArticleRead:
        object_id = self._to_object_id(article_id)
        if object_id is None:
            raise ArticleNotFoundError("Article was not found.")

        # A read is not an edit: bumping updated_at here would make every
        # "recently updated" sort reflect traffic instead of editorial work.
        updated_article = await self.collection.find_one_and_update(
            {"_id": object_id},
            {"$inc": {"views": 1}},
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
        elif query.category_ids:
            article_filter["category_id"] = {"$in": query.category_ids}
        if query.tag is not None:
            article_filter["tags"] = query.tag
        if query.is_featured is not None:
            article_filter["is_featured"] = query.is_featured
        if query.article_format is not None:
            article_filter["article_format"] = query.article_format
        if query.is_editors_pick is not None:
            article_filter["is_editors_pick"] = self._boolean_flag_filter(
                query.is_editors_pick
            )
        if query.author is not None:
            article_filter["author"] = query.author
        if query.author_id is not None:
            article_filter["author_id"] = query.author_id
        if query.published_from is not None or query.published_to is not None:
            article_filter["published_at"] = self._date_range_filter(
                query.published_from,
                query.published_to,
            )
        if query.search is not None:
            article_filter["$text"] = {"$search": query.search}

        return article_filter

    def _build_sort(self, query: ArticleQueryParams) -> list[tuple[str, int]]:
        sort_direction = ASCENDING if query.sort_direction == "asc" else DESCENDING

        return [
            (query.sort_by, sort_direction),
            ("_id", sort_direction),
        ]

    def _boolean_flag_filter(self, value: bool) -> Any:
        # Articles created before these flags existed have no such field, so a
        # plain False would skip them. $ne treats "missing" as "not set".
        return True if value else {"$ne": True}

    def _date_range_filter(
        self,
        start: datetime | None,
        end: datetime | None,
    ) -> dict[str, datetime]:
        date_filter: dict[str, datetime] = {}

        if start is not None:
            date_filter["$gte"] = start
        if end is not None:
            date_filter["$lte"] = end

        return date_filter

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
