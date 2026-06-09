import re
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database.mongodb import get_database
from app.models.tag import TAG_COLLECTION, create_tag_document
from app.schemas.tag import (
    TagCreate,
    TagListResponse,
    TagQueryParams,
    TagRead,
    TagUpdate,
)


class TagServiceError(Exception):
    pass


class TagNotFoundError(TagServiceError):
    pass


class TagSlugConflictError(TagServiceError):
    pass


class TagService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.database[TAG_COLLECTION]

    async def create_tag(self, payload: TagCreate) -> TagRead:
        tag_document = create_tag_document(**payload.model_dump())

        try:
            result = await self.collection.insert_one(tag_document.to_mongo())
        except DuplicateKeyError as exc:
            raise TagSlugConflictError(
                "A tag with this slug already exists."
            ) from exc

        created_tag = await self.collection.find_one({"_id": result.inserted_id})
        if created_tag is None:
            raise TagNotFoundError("Created tag could not be loaded.")

        return self._to_tag_read(created_tag)

    async def get_tag_by_id(self, tag_id: str) -> TagRead | None:
        object_id = self._to_object_id(tag_id)
        if object_id is None:
            return None

        tag = await self.collection.find_one({"_id": object_id})
        if tag is None:
            return None

        return self._to_tag_read(tag)

    async def get_tag_by_slug(self, slug: str) -> TagRead | None:
        tag = await self.collection.find_one({"slug": slug.strip().lower()})
        if tag is None:
            return None

        return self._to_tag_read(tag)

    async def get_tag_detail(self, identifier: str) -> TagRead | None:
        clean_identifier = identifier.strip().lower()

        tag = await self.get_tag_by_id(clean_identifier)
        if tag is not None:
            return tag

        return await self.get_tag_by_slug(clean_identifier)

    async def list_tags(self, query: TagQueryParams) -> TagListResponse:
        tag_filter = self._build_filter(query)
        skip = (query.page - 1) * query.per_page

        cursor = (
            self.collection.find(tag_filter)
            .sort(self._build_sort(query))
            .skip(skip)
            .limit(query.per_page)
        )
        tags = [self._to_tag_read(tag) async for tag in cursor]
        total = await self.collection.count_documents(tag_filter)

        return TagListResponse(
            items=tags,
            total=total,
            page=query.page,
            per_page=query.per_page,
            total_pages=0,
            sort_by=query.sort_by,
            sort_direction=query.sort_direction,
        )

    async def update_tag(
        self,
        tag_id: str,
        payload: TagUpdate,
    ) -> TagRead:
        object_id = self._to_object_id(tag_id)
        if object_id is None:
            raise TagNotFoundError("Tag was not found.")

        update_data = payload.model_dump(exclude_unset=True)

        try:
            updated_tag = await self.collection.find_one_and_update(
                {"_id": object_id},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            raise TagSlugConflictError(
                "A tag with this slug already exists."
            ) from exc

        if updated_tag is None:
            raise TagNotFoundError("Tag was not found.")

        return self._to_tag_read(updated_tag)

    async def delete_tag(self, tag_id: str) -> bool:
        object_id = self._to_object_id(tag_id)
        if object_id is None:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count == 1

    def _build_filter(self, query: TagQueryParams) -> dict[str, Any]:
        tag_filter: dict[str, Any] = {}

        if query.search is not None:
            escaped_search = re.escape(query.search)
            tag_filter["$or"] = [
                {"name": {"$regex": escaped_search, "$options": "i"}},
                {"slug": {"$regex": escaped_search, "$options": "i"}},
            ]

        return tag_filter

    def _build_sort(self, query: TagQueryParams) -> list[tuple[str, int]]:
        sort_direction = ASCENDING if query.sort_direction == "asc" else DESCENDING

        return [
            (query.sort_by, sort_direction),
            ("_id", sort_direction),
        ]

    def _to_tag_read(self, tag: dict[str, Any]) -> TagRead:
        return TagRead.model_validate(tag)

    def _to_object_id(self, value: str) -> ObjectId | None:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None


def get_tag_service(
    database: AsyncIOMotorDatabase | None = None,
) -> TagService:
    return TagService(database=database)
