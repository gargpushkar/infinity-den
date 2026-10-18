from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT

from app.database.mongodb import get_database
from app.models.admin import ADMIN_COLLECTION
from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.models.newsletter import NEWSLETTER_SUBSCRIBER_COLLECTION
from app.models.bookmark import BOOKMARK_COLLECTION
from app.models.comment import COMMENT_COLLECTION
from app.models.debate import ARGUMENT_COLLECTION, DEBATE_COLLECTION, RATING_COLLECTION, REBUTTAL_COLLECTION, STANCE_COLLECTION
from app.models.deletion_request import DELETION_REQUEST_COLLECTION
from app.models.question import QUESTION_COLLECTION, RESPONSE_COLLECTION
from app.models.report import REPORT_COLLECTION
from app.models.quiz import QUIZ_COLLECTION
from app.models.submission import ARTICLE_SUBMISSION_COLLECTION
from app.models.tag import TAG_COLLECTION
from app.models.user import USER_COLLECTION


async def create_indexes() -> None:
    db = get_database()

    await _create_article_indexes(db)

    await db[CATEGORY_COLLECTION].create_index([("slug", ASCENDING)], unique=True)
    await db[TAG_COLLECTION].create_index([("slug", ASCENDING)], unique=True)
    await db[USER_COLLECTION].create_index([("username", ASCENDING)], unique=True)
    await db[USER_COLLECTION].create_index([("email", ASCENDING)], unique=True)
    # MongoDB deletes unconfirmed sign-ups once pending_expires_at passes.
    await db[USER_COLLECTION].create_index([("pending_expires_at", ASCENDING)], expireAfterSeconds=0)
    # One question per day; one response per member per question.
    await db[QUESTION_COLLECTION].create_index([("publish_date", ASCENDING)], unique=True)
    await db[QUESTION_COLLECTION].create_index([("slug", ASCENDING)], unique=True)
    await db[QUESTION_COLLECTION].create_index([("status", ASCENDING), ("publish_date", DESCENDING)])
    await db[RESPONSE_COLLECTION].create_index(
        [("question_id", ASCENDING), ("user_id", ASCENDING)], unique=True
    )
    await db[RESPONSE_COLLECTION].create_index(
        [("question_id", ASCENDING), ("status", ASCENDING), ("is_featured", DESCENDING), ("created_at", DESCENDING)]
    )
    await db[RESPONSE_COLLECTION].create_index(
        [("user_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)]
    )
    # One argument and one stance per member per debate; one rebuttal and one rating per member per argument.
    await db[DEBATE_COLLECTION].create_index([("slug", ASCENDING)], unique=True)
    await db[DEBATE_COLLECTION].create_index([("status", ASCENDING), ("closes_on", DESCENDING)])
    await db[ARGUMENT_COLLECTION].create_index([("debate_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
    await db[ARGUMENT_COLLECTION].create_index(
        [("debate_id", ASCENDING), ("status", ASCENDING), ("is_featured", DESCENDING), ("created_at", DESCENDING)]
    )
    await db[ARGUMENT_COLLECTION].create_index([("user_id", ASCENDING)])
    await db[REBUTTAL_COLLECTION].create_index([("argument_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
    await db[REBUTTAL_COLLECTION].create_index([("debate_id", ASCENDING), ("status", ASCENDING), ("created_at", ASCENDING)])
    await db[REBUTTAL_COLLECTION].create_index([("user_id", ASCENDING)])
    await db[RATING_COLLECTION].create_index([("argument_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
    await db[RATING_COLLECTION].create_index([("debate_id", ASCENDING), ("user_id", ASCENDING)])
    await db[RATING_COLLECTION].create_index([("user_id", ASCENDING)])
    await db[STANCE_COLLECTION].create_index([("debate_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
    await db[STANCE_COLLECTION].create_index([("user_id", ASCENDING)])
    await db[COMMENT_COLLECTION].create_index([("article_id", ASCENDING), ("status", ASCENDING), ("created_at", ASCENDING)])
    await db[COMMENT_COLLECTION].create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db[BOOKMARK_COLLECTION].create_index([("user_id", ASCENDING), ("article_id", ASCENDING)], unique=True)
    await db[BOOKMARK_COLLECTION].create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db[REPORT_COLLECTION].create_index([("status", ASCENDING), ("created_at", ASCENDING)])
    await db[DELETION_REQUEST_COLLECTION].create_index([("status", ASCENDING), ("requested_at", ASCENDING)])
    await db[DELETION_REQUEST_COLLECTION].create_index([("user_id", ASCENDING), ("status", ASCENDING)])
    await db[REPORT_COLLECTION].create_index([("target_type", ASCENDING), ("target_id", ASCENDING), ("status", ASCENDING)])
    await db[REPORT_COLLECTION].create_index([("reporter_id", ASCENDING), ("target_id", ASCENDING), ("status", ASCENDING)])
    await db[QUIZ_COLLECTION].create_index([("slug", ASCENDING)], unique=True)
    await db[QUIZ_COLLECTION].create_index([("status", ASCENDING)])
    await db[NEWSLETTER_SUBSCRIBER_COLLECTION].create_index(
        [("email", ASCENDING)],
        unique=True,
    )
    await db[ARTICLE_SUBMISSION_COLLECTION].create_index(
        [("status", ASCENDING), ("created_at", DESCENDING)]
    )
    await db[ARTICLE_SUBMISSION_COLLECTION].create_index(
        [("email", ASCENDING), ("created_at", DESCENDING)]
    )
    await db[ADMIN_COLLECTION].create_index([("username", ASCENDING)], unique=True)
    await db[ADMIN_COLLECTION].create_index(
        [("role", ASCENDING), ("is_active", ASCENDING)]
    )
    await db[ADMIN_COLLECTION].create_index([("created_at", DESCENDING)])


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
    await articles.create_index(
        [
            ("article_format", ASCENDING),
            ("status", ASCENDING),
            ("published_at", DESCENDING),
        ]
    )
    await articles.create_index(
        [
            ("is_editors_pick", ASCENDING),
            ("status", ASCENDING),
            ("published_at", DESCENDING),
        ]
    )
    await articles.create_index(
        [("author_id", ASCENDING), ("status", ASCENDING), ("published_at", DESCENDING)]
    )
    await articles.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    await articles.create_index([("status", ASCENDING), ("updated_at", DESCENDING)])
    await articles.create_index([("status", ASCENDING), ("title", ASCENDING)])
    await articles.create_index([("title", TEXT), ("excerpt", TEXT), ("content", TEXT)])
