from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.database.mongodb import get_database
from app.models.newsletter import (
    NEWSLETTER_SUBSCRIBER_COLLECTION,
    create_newsletter_subscriber_document,
)
from app.schemas.newsletter import (
    NewsletterSubscriberRead,
    NewsletterSubscriptionCreate,
)


class NewsletterServiceError(Exception):
    pass


class NewsletterSubscriberConflictError(NewsletterServiceError):
    pass


class NewsletterService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.database[NEWSLETTER_SUBSCRIBER_COLLECTION]

    async def create_subscription(
        self,
        payload: NewsletterSubscriptionCreate,
    ) -> NewsletterSubscriberRead:
        subscriber_document = create_newsletter_subscriber_document(
            email=payload.email,
        )

        try:
            result = await self.collection.insert_one(subscriber_document.to_mongo())
        except DuplicateKeyError as exc:
            raise NewsletterSubscriberConflictError(
                "This email is already subscribed."
            ) from exc

        created_subscriber = await self.collection.find_one({"_id": result.inserted_id})
        if created_subscriber is None:
            raise NewsletterServiceError("Created subscriber could not be loaded.")

        return NewsletterSubscriberRead.model_validate(created_subscriber)


def get_newsletter_service(
    database: AsyncIOMotorDatabase | None = None,
) -> NewsletterService:
    return NewsletterService(database=database)
