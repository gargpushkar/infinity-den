import re
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database.mongodb import get_database
from app.models.category import CATEGORY_COLLECTION, create_category_document
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryQueryParams,
    CategoryRead,
    CategoryUpdate,
)


class CategoryServiceError(Exception):
    pass


class CategoryNotFoundError(CategoryServiceError):
    pass


class CategorySlugConflictError(CategoryServiceError):
    pass


class CategoryService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.database[CATEGORY_COLLECTION]

    async def create_category(self, payload: CategoryCreate) -> CategoryRead:
        category_document = create_category_document(**payload.model_dump())

        try:
            result = await self.collection.insert_one(category_document.to_mongo())
        except DuplicateKeyError as exc:
            raise CategorySlugConflictError(
                "A category with this slug already exists."
            ) from exc

        created_category = await self.collection.find_one({"_id": result.inserted_id})
        if created_category is None:
            raise CategoryNotFoundError("Created category could not be loaded.")

        return self._to_category_read(created_category)

    async def get_category_by_id(self, category_id: str) -> CategoryRead | None:
        object_id = self._to_object_id(category_id)
        if object_id is None:
            return None

        category = await self.collection.find_one({"_id": object_id})
        if category is None:
            return None

        return self._to_category_read(category)

    async def get_category_by_slug(self, slug: str) -> CategoryRead | None:
        category = await self.collection.find_one({"slug": slug.strip().lower()})
        if category is None:
            return None

        return self._to_category_read(category)

    async def get_category_detail(self, identifier: str) -> CategoryRead | None:
        clean_identifier = identifier.strip().lower()

        category = await self.get_category_by_id(clean_identifier)
        if category is not None:
            return category

        return await self.get_category_by_slug(clean_identifier)

    async def list_categories(self, query: CategoryQueryParams) -> CategoryListResponse:
        category_filter = self._build_filter(query)
        skip = (query.page - 1) * query.per_page

        cursor = (
            self.collection.find(category_filter)
            .sort(self._build_sort(query))
            .skip(skip)
            .limit(query.per_page)
        )
        categories = [self._to_category_read(category) async for category in cursor]
        total = await self.collection.count_documents(category_filter)

        return CategoryListResponse(
            items=categories,
            total=total,
            page=query.page,
            per_page=query.per_page,
            total_pages=0,
            sort_by=query.sort_by,
            sort_direction=query.sort_direction,
        )

    async def update_category(
        self,
        category_id: str,
        payload: CategoryUpdate,
    ) -> CategoryRead:
        object_id = self._to_object_id(category_id)
        if object_id is None:
            raise CategoryNotFoundError("Category was not found.")

        update_data = payload.model_dump(exclude_unset=True)

        try:
            updated_category = await self.collection.find_one_and_update(
                {"_id": object_id},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            raise CategorySlugConflictError(
                "A category with this slug already exists."
            ) from exc

        if updated_category is None:
            raise CategoryNotFoundError("Category was not found.")

        return self._to_category_read(updated_category)

    async def delete_category(self, category_id: str) -> bool:
        object_id = self._to_object_id(category_id)
        if object_id is None:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count == 1

    def _build_filter(self, query: CategoryQueryParams) -> dict[str, Any]:
        category_filter: dict[str, Any] = {}

        if query.search is not None:
            escaped_search = re.escape(query.search)
            category_filter["$or"] = [
                {"name": {"$regex": escaped_search, "$options": "i"}},
                {"slug": {"$regex": escaped_search, "$options": "i"}},
                {"description": {"$regex": escaped_search, "$options": "i"}},
            ]

        return category_filter

    def _build_sort(self, query: CategoryQueryParams) -> list[tuple[str, int]]:
        sort_direction = ASCENDING if query.sort_direction == "asc" else DESCENDING

        return [
            (query.sort_by, sort_direction),
            ("_id", sort_direction),
        ]

    def _to_category_read(self, category: dict[str, Any]) -> CategoryRead:
        return CategoryRead.model_validate(category)

    def _to_object_id(self, value: str) -> ObjectId | None:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None


def get_category_service(
    database: AsyncIOMotorDatabase | None = None,
) -> CategoryService:
    return CategoryService(database=database)
