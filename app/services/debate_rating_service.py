"""Rating Debate Den arguments on clarity, evidence, and reasoning (1-5 each).

Ratings judge how well something is argued, not whether the reader agrees.
They never change the order of arguments. Averages appear only once
RATINGS_NEEDED members have rated, and only to members who have rated that
argument themselves, or to everyone once the debate closes, so early ratings
don't steer later ones. Nobody, editors included, sees who gave which rating.
"""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config.constants import RATING_DIMENSIONS
from app.database.mongodb import get_database
from app.models.debate import ARGUMENT_COLLECTION, RATING_COLLECTION, RatingDocument
from app.schemas.debate import DebateRead, RatingInput
from app.schemas.user import MemberRead
from app.services.debate_service import DebateClosedError, DebateNotFoundError, OwnArgumentError, is_open


# ponytail: averages are computed in Python from every rating in the debate;
# fine for thousands. Switch to a $group/$avg aggregation if debates get huge.
RATING_LIMIT = 20_000


def _object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


class DebateRatingService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.ratings = self.database[RATING_COLLECTION]
        self.arguments = self.database[ARGUMENT_COLLECTION]

    async def save_rating(
        self, debate: DebateRead, argument_id: str, member: MemberRead, payload: RatingInput, today: str
    ) -> dict[str, Any]:
        """Create or replace the member's rating of this argument."""
        if not is_open(debate, today):
            raise DebateClosedError("This debate is closed, so its ratings are final.")
        argument = await self.arguments.find_one(
            {"_id": _object_id(argument_id), "debate_id": debate.id, "status": "published"}
        )
        if argument is None:
            raise DebateNotFoundError("That argument is no longer here.")
        if argument["user_id"] == member.id:
            raise OwnArgumentError("You can't rate your own argument.")

        scores = payload.model_dump()
        existing = await self.ratings.find_one_and_update(
            {"argument_id": argument_id, "user_id": member.id},
            {"$set": {**scores, "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        if existing is not None:
            return existing

        document = RatingDocument(debate_id=debate.id, argument_id=argument_id, user_id=member.id, **scores).to_mongo()
        try:
            await self.ratings.insert_one(document)
        except DuplicateKeyError:
            # Two submissions raced; the unique index kept one. Update that one.
            return await self.save_rating(debate, argument_id, member, payload, today)
        return document

    async def member_ratings(self, debate_id: str, member: MemberRead) -> dict[str, dict[str, int]]:
        """The member's own scores in this debate, by argument id."""
        cursor = self.ratings.find({"debate_id": debate_id, "user_id": member.id})
        return {document["argument_id"]: _scores(document) async for document in cursor}

    async def averages(self, debate_id: str) -> dict[str, dict[str, Any]]:
        """Per argument: the count and each dimension's average, to one decimal."""
        totals: dict[str, dict[str, int]] = {}
        async for document in self.ratings.find({"debate_id": debate_id}).limit(RATING_LIMIT):
            total = totals.setdefault(document["argument_id"], {"count": 0, **{key: 0 for key in RATING_DIMENSIONS}})
            total["count"] += 1
            for key in RATING_DIMENSIONS:
                total[key] += document[key]
        return {
            argument_id: {"count": total["count"], **{key: round(total[key] / total["count"], 1) for key in RATING_DIMENSIONS}}
            for argument_id, total in totals.items()
        }


def _scores(document: dict[str, Any]) -> dict[str, int]:
    return {key: document[key] for key in RATING_DIMENSIONS}
