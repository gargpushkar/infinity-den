from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.database.mongodb import get_database
from app.models.submission import (
    ARTICLE_SUBMISSION_COLLECTION,
    SubmissionStatus,
    create_article_submission_document,
)
from app.schemas.submission import (
    ArticleSubmissionCreate,
    ArticleSubmissionListResponse,
    ArticleSubmissionRead,
)


class SubmissionServiceError(Exception):
    pass


class SubmissionNotFoundError(SubmissionServiceError):
    pass


class SubmissionService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.database[ARTICLE_SUBMISSION_COLLECTION]

    async def create_submission(
        self,
        payload: ArticleSubmissionCreate,
    ) -> ArticleSubmissionRead:
        submission_document = create_article_submission_document(
            **payload.model_dump()
        )
        result = await self.collection.insert_one(submission_document.to_mongo())
        created_submission = await self.collection.find_one({"_id": result.inserted_id})
        if created_submission is None:
            raise SubmissionServiceError("Created submission could not be loaded.")

        return ArticleSubmissionRead.model_validate(created_submission)

    async def list_submissions(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        status: SubmissionStatus | None = None,
    ) -> ArticleSubmissionListResponse:
        submission_filter: dict[str, str] = {}
        if status is not None:
            submission_filter["status"] = status

        skip = (page - 1) * per_page
        cursor = (
            self.collection.find(submission_filter)
            .sort([("created_at", DESCENDING), ("_id", ASCENDING)])
            .skip(skip)
            .limit(per_page)
        )
        submissions = [
            ArticleSubmissionRead.model_validate(submission)
            async for submission in cursor
        ]
        total = await self.collection.count_documents(submission_filter)

        return ArticleSubmissionListResponse(
            items=submissions,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=0,
        )

    async def update_submission_status(
        self,
        submission_id: str,
        status: SubmissionStatus,
    ) -> ArticleSubmissionRead:
        object_id = self._to_object_id(submission_id)
        if object_id is None:
            raise SubmissionNotFoundError("Submission was not found.")

        updated_submission = await self.collection.find_one_and_update(
            {"_id": object_id},
            {"$set": {"status": status}},
            return_document=ReturnDocument.AFTER,
        )
        if updated_submission is None:
            raise SubmissionNotFoundError("Submission was not found.")

        return ArticleSubmissionRead.model_validate(updated_submission)

    def _to_object_id(self, value: str) -> ObjectId | None:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None


def get_submission_service(
    database: AsyncIOMotorDatabase | None = None,
) -> SubmissionService:
    return SubmissionService(database=database)
