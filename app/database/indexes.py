from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT

from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION


async def create_indexes() -> None:
    db = get_database()

    await _create_article_indexes(db)

    await db[CATEGORY_COLLECTION].create_index([("slug", ASCENDING)], unique=True)
    await db.tags.create_index([("slug", ASCENDING)], unique=True)
    await db.newsletter_subscribers.create_index([("email", ASCENDING)], unique=True)


async def _create_article_indexes(db: AsyncIOMotorDatabase) -> None:
    articles = db[ARTICLE_COLLECTION]

    await articles.create_index([("slug", ASCENDING)], unique=True)
    await articles.create_index([("status", ASCENDING), ("published_at", DESCENDING)])
    await articles.create_index(
        [
            ("category_id", ASCENDING),
            ("status", ASCENDING),
            ("published_at", DESCENDING),
        ]
    )
    await articles.create_index(
        [
            ("tags", ASCENDING),
            ("status", ASCENDING),
            ("published_at", DESCENDING),
        ]
    )
    await articles.create_index(
        [
            ("is_featured", ASCENDING),
            ("status", ASCENDING),
            ("published_at", DESCENDING),
        ]
    )
    await articles.create_index([("status", ASCENDING), ("views", DESCENDING)])
    await articles.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    await articles.create_index([("status", ASCENDING), ("updated_at", DESCENDING)])
    await articles.create_index([("status", ASCENDING), ("title", ASCENDING)])
    await articles.create_index([("title", TEXT), ("excerpt", TEXT), ("content", TEXT)])
