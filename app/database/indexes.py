from pymongo import ASCENDING, DESCENDING, TEXT

from app.database.mongodb import get_database


async def create_indexes() -> None:
    db = get_database()

    await db.articles.create_index([("slug", ASCENDING)], unique=True)
    await db.articles.create_index([("status", ASCENDING), ("published_at", DESCENDING)])
    await db.articles.create_index([("title", TEXT), ("excerpt", TEXT), ("content", TEXT)])

    await db.categories.create_index([("slug", ASCENDING)], unique=True)
    await db.tags.create_index([("slug", ASCENDING)], unique=True)
    await db.newsletter_subscribers.create_index([("email", ASCENDING)], unique=True)
