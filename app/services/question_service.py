"""The Question Room: curated daily questions and members' responses.

Responses publish immediately (editors can hide them); there are no votes,
and editors feature the most insightful ones (vision.md -> Question Room).
"""

import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config.settings import settings
from app.database.mongodb import get_database
from app.models.question import (
    QUESTION_COLLECTION,
    RESPONSE_COLLECTION,
    QuestionDocument,
    ResponseDocument,
)
from app.schemas.question import (
    AdminResponseUpdate,
    QuestionInput,
    QuestionRead,
    ResponseInput,
    ResponseRead,
)
from app.schemas.user import MemberRead


PAST_QUESTION_LIMIT = 30
RESPONSE_LIMIT = 200


class QuestionServiceError(Exception):
    pass


class QuestionNotFoundError(QuestionServiceError):
    pass


class QuestionDateTakenError(QuestionServiceError):
    pass


def site_today(now: datetime | None = None) -> str:
    """Today's date where the audience is, as "YYYY-MM-DD"."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(ZoneInfo(settings.site_timezone)).date().isoformat()


def question_slug(text: str, publish_date: str) -> str:
    words = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].strip("-")
    return f"{publish_date}-{words or 'question'}"


def _object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


class QuestionService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.questions = self.database[QUESTION_COLLECTION]
        self.responses = self.database[RESPONSE_COLLECTION]

    # --- editors -------------------------------------------------------------

    async def create_question(self, payload: QuestionInput) -> QuestionRead:
        publish_date = payload.publish_date.isoformat()
        document = QuestionDocument(
            text=payload.text,
            slug=question_slug(payload.text, publish_date),
            publish_date=publish_date,
            intro=payload.intro,
            category_id=payload.category_id,
            status=payload.status,
        ).to_mongo()
        try:
            result = await self.questions.insert_one(document)
        except DuplicateKeyError as exc:
            raise QuestionDateTakenError("Another question is already scheduled for that date.") from exc

        return QuestionRead.model_validate({**document, "_id": result.inserted_id})

    async def update_question(self, question_id: str, payload: QuestionInput) -> QuestionRead:
        # The slug stays as created so links to the question never break.
        update = {
            "text": payload.text,
            "intro": payload.intro,
            "category_id": payload.category_id,
            "publish_date": payload.publish_date.isoformat(),
            "status": payload.status,
            "updated_at": datetime.now(timezone.utc),
        }
        try:
            document = await self.questions.find_one_and_update(
                {"_id": _object_id(question_id)},
                {"$set": update},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            raise QuestionDateTakenError("Another question is already scheduled for that date.") from exc
        if document is None:
            raise QuestionNotFoundError("Question was not found.")

        return QuestionRead.model_validate(document)

    async def delete_question(self, question_id: str) -> bool:
        result = await self.questions.delete_one({"_id": _object_id(question_id)})
        if result.deleted_count:
            await self.responses.delete_many({"question_id": question_id})
        return bool(result.deleted_count)

    async def list_questions(self) -> list[QuestionRead]:
        cursor = self.questions.find({}).sort([("publish_date", DESCENDING)]).limit(200)
        return [QuestionRead.model_validate(document) async for document in cursor]

    async def get_question(self, question_id: str) -> QuestionRead | None:
        document = await self.questions.find_one({"_id": _object_id(question_id)})
        return QuestionRead.model_validate(document) if document else None

    async def all_responses(self, question_id: str) -> list[ResponseRead]:
        cursor = self.responses.find({"question_id": question_id}).sort([("created_at", DESCENDING)])
        return [ResponseRead.model_validate(document) async for document in cursor]

    async def moderate_response(self, response_id: str, payload: AdminResponseUpdate) -> ResponseRead:
        document = await self.responses.find_one_and_update(
            {"_id": _object_id(response_id)},
            {"$set": {**payload.model_dump(exclude_unset=True), "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            raise QuestionNotFoundError("Response was not found.")
        return ResponseRead.model_validate(document)

    # --- readers -------------------------------------------------------------

    def _live(self, today: str) -> dict[str, Any]:
        # Published and not scheduled for the future.
        return {"status": "published", "publish_date": {"$lte": today}}

    async def current_question(self, today: str) -> QuestionRead | None:
        """Today's question, or the latest one if nothing is scheduled today."""
        document = await self.questions.find_one(self._live(today), sort=[("publish_date", DESCENDING)])
        return QuestionRead.model_validate(document) if document else None

    async def get_live_question(self, slug: str, today: str) -> QuestionRead | None:
        document = await self.questions.find_one({**self._live(today), "slug": slug})
        return QuestionRead.model_validate(document) if document else None

    async def past_questions(self, today: str, *, exclude_id: str | None) -> list[QuestionRead]:
        query = self._live(today)
        if exclude_id:
            query["_id"] = {"$ne": _object_id(exclude_id)}
        cursor = self.questions.find(query).sort([("publish_date", DESCENDING)]).limit(PAST_QUESTION_LIMIT)
        return [QuestionRead.model_validate(document) async for document in cursor]

    async def public_responses(self, question_id: str) -> list[ResponseRead]:
        """Featured first, then newest. Hidden responses never appear."""
        cursor = (
            self.responses.find({"question_id": question_id, "status": "published"})
            .sort([("is_featured", DESCENDING), ("created_at", DESCENDING)])
            .limit(RESPONSE_LIMIT)
        )
        return [ResponseRead.model_validate(document) async for document in cursor]

    async def response_counts(self, question_ids: list[str]) -> dict[str, int]:
        pipeline = [
            {"$match": {"question_id": {"$in": question_ids}, "status": "published"}},
            {"$group": {"_id": "$question_id", "count": {"$sum": 1}}},
        ]
        return {row["_id"]: row["count"] async for row in self.responses.aggregate(pipeline)}

    async def member_public_responses(self, user_id: str) -> list[dict[str, Any]]:
        """A member's visible responses with their questions, for the profile."""
        cursor = (
            self.responses.find({"user_id": user_id, "status": "published"})
            .sort([("created_at", DESCENDING)])
            .limit(50)
        )
        responses = [ResponseRead.model_validate(document) async for document in cursor]
        ids = [_object_id(r.question_id) for r in responses]
        questions = {
            str(document["_id"]): QuestionRead.model_validate(document)
            async for document in self.questions.find({"_id": {"$in": ids}, "status": "published"})
        }
        return [
            {"response": response, "question": questions[response.question_id]}
            for response in responses
            if response.question_id in questions
        ]

    # --- members -------------------------------------------------------------

    async def member_response(self, question_id: str, member: MemberRead) -> ResponseRead | None:
        document = await self.responses.find_one({"question_id": question_id, "user_id": member.id})
        return ResponseRead.model_validate(document) if document else None

    async def save_response(self, question: QuestionRead, member: MemberRead, payload: ResponseInput) -> ResponseRead:
        """Create or replace the member's one response to this question.

        Editing keeps the editors' decisions: a hidden response stays hidden
        and a featured one stays featured.
        """
        now = datetime.now(timezone.utc)
        sources = [source.model_dump() for source in payload.sources]
        existing = await self.responses.find_one_and_update(
            {"question_id": question.id, "user_id": member.id},
            {"$set": {"kind": payload.kind, "body": payload.body, "sources": sources, "author": member.display_name, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if existing is not None:
            return ResponseRead.model_validate(existing)

        document = ResponseDocument(
            question_id=question.id,
            user_id=member.id,
            author=member.display_name,
            author_username=member.username,
            kind=payload.kind,
            body=payload.body,
            sources=sources,
        ).to_mongo()
        try:
            result = await self.responses.insert_one(document)
        except DuplicateKeyError:
            # Two submissions raced; the unique index kept one. Edit that one.
            return await self.save_response(question, member, payload)
        return ResponseRead.model_validate({**document, "_id": result.inserted_id})

    async def delete_response(self, question_id: str, member: MemberRead) -> bool:
        result = await self.responses.delete_one({"question_id": question_id, "user_id": member.id})
        return bool(result.deleted_count)
