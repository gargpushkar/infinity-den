from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.models.submission import (
    ARTICLE_SUBMISSION_COLLECTION,
    create_article_submission_document,
)
from app.schemas.submission import ArticleSubmissionCreate, ArticleSubmissionRead


class SubmissionServiceError(Exception):
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


def get_submission_service(
    database: AsyncIOMotorDatabase | None = None,
) -> SubmissionService:
    return SubmissionService(database=database)
