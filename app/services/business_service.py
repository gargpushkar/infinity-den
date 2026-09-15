import re
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database.mongodb import get_database
from app.models.business import BUSINESS_COLLECTION, create_business_document
from app.schemas.business import (
    BusinessCreate,
    BusinessListResponse,
    BusinessQueryParams,
    BusinessRead,
    BusinessUpdate,
)


class BusinessServiceError(Exception):
    pass


class BusinessNotFoundError(BusinessServiceError):
    pass


class BusinessSlugConflictError(BusinessServiceError):
    pass


class BusinessService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.database[BUSINESS_COLLECTION]

    async def create_business(self, payload: BusinessCreate) -> BusinessRead:
        business_document = create_business_document(**payload.model_dump())

        try:
            result = await self.collection.insert_one(business_document.to_mongo())
        except DuplicateKeyError as exc:
            raise BusinessSlugConflictError(
                "A business with this slug already exists."
            ) from exc

        created_business = await self.collection.find_one({"_id": result.inserted_id})
        if created_business is None:
            raise BusinessNotFoundError("Created business could not be loaded.")

        return self._to_business_read(created_business)

    async def get_business_by_id(self, business_id: str) -> BusinessRead | None:
        object_id = self._to_object_id(business_id)
        if object_id is None:
            return None

        business = await self.collection.find_one({"_id": object_id})
        if business is None:
            return None

        return self._to_business_read(business)

    async def get_business_by_slug(self, slug: str) -> BusinessRead | None:
        business = await self.collection.find_one({"slug": slug.strip().lower()})
        if business is None:
            return None

        return self._to_business_read(business)

    async def get_business_detail(self, identifier: str) -> BusinessRead | None:
        clean_identifier = identifier.strip().lower()

        business = await self.get_business_by_id(clean_identifier)
        if business is not None:
            return business

        return await self.get_business_by_slug(clean_identifier)

    async def list_businesses(self, query: BusinessQueryParams) -> BusinessListResponse:
        business_filter = self._build_filter(query)
        skip = (query.page - 1) * query.per_page

        cursor = (
            self.collection.find(business_filter)
            .sort(self._build_sort(query))
            .skip(skip)
            .limit(query.per_page)
        )
        businesses = [self._to_business_read(business) async for business in cursor]
        total = await self.collection.count_documents(business_filter)

        return BusinessListResponse(
            items=businesses,
            total=total,
            page=query.page,
            per_page=query.per_page,
            total_pages=0,
            sort_by=query.sort_by,
            sort_direction=query.sort_direction,
        )

    async def update_business(
        self,
        business_id: str,
        payload: BusinessUpdate,
    ) -> BusinessRead:
        object_id = self._to_object_id(business_id)
        if object_id is None:
            raise BusinessNotFoundError("Business was not found.")

        update_data = payload.model_dump(exclude_unset=True)
        update_data["updated_at"] = self._utc_now()

        try:
            updated_business = await self.collection.find_one_and_update(
                {"_id": object_id},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            raise BusinessSlugConflictError(
                "A business with this slug already exists."
            ) from exc

        if updated_business is None:
            raise BusinessNotFoundError("Business was not found.")

        return self._to_business_read(updated_business)

    async def delete_business(self, business_id: str) -> bool:
        object_id = self._to_object_id(business_id)
        if object_id is None:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count == 1

    def _build_filter(self, query: BusinessQueryParams) -> dict[str, Any]:
        business_filter: dict[str, Any] = {}

        if query.search is not None:
            escaped_search = re.escape(query.search)
            business_filter["$or"] = [
                {"name": {"$regex": escaped_search, "$options": "i"}},
                {"slug": {"$regex": escaped_search, "$options": "i"}},
                {"tagline": {"$regex": escaped_search, "$options": "i"}},
                {"location": {"$regex": escaped_search, "$options": "i"}},
            ]
        if query.category_id is not None:
            business_filter["category_id"] = query.category_id
        if query.is_featured is not None:
            # Businesses created before this flag existed have no such field.
            business_filter["is_featured"] = (
                True if query.is_featured else {"$ne": True}
            )

        return business_filter

    def _build_sort(self, query: BusinessQueryParams) -> list[tuple[str, int]]:
        sort_direction = ASCENDING if query.sort_direction == "asc" else DESCENDING

        # Sort order is a manual ranking, so ties fall back to name rather than
        # an arbitrary insertion order.
        if query.sort_by == "sort_order":
            return [("sort_order", sort_direction), ("name", ASCENDING)]

        return [(query.sort_by, sort_direction), ("_id", sort_direction)]

    def _to_business_read(self, business: dict[str, Any]) -> BusinessRead:
        return BusinessRead.model_validate(business)

    def _to_object_id(self, value: str) -> ObjectId | None:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)


def get_business_service(
    database: AsyncIOMotorDatabase | None = None,
) -> BusinessService:
    return BusinessService(database=database)
