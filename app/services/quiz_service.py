"""Fact or Fiction: the first Curiosity Arcade game.

Answering is a plain link (?answer=fact|fiction) and nothing is stored, so
there is no per-visitor state and no answer statistics in Phase 1.
"""

import random
import re
import secrets
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.quiz import QUIZ_COLLECTION, QuizItemDocument
from app.schemas.quiz import QuizItemInput, QuizItemRead


ANSWERS = {"fact": True, "fiction": False}


class QuizServiceError(Exception):
    pass


class QuizItemNotFoundError(QuizServiceError):
    pass


class QuizArticleNotFoundError(QuizServiceError):
    pass


def quiz_slug(claim: str) -> str:
    words = re.sub(r"[^a-z0-9]+", "-", claim.lower()).strip("-")[:60].strip("-") or "claim"
    return f"{words}-{secrets.token_hex(2)}"


def is_correct(item: QuizItemRead, answer: str) -> bool | None:
    """True or False for a valid answer, None when no (or a junk) answer was given."""
    if answer not in ANSWERS:
        return None
    return ANSWERS[answer] == item.is_true


def _object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


class QuizService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.items = self.database[QUIZ_COLLECTION]

    # --- editors -------------------------------------------------------------

    async def create_item(self, payload: QuizItemInput) -> QuizItemRead:
        await self._check_article(payload.article_slug)
        document = QuizItemDocument(slug=quiz_slug(payload.claim), **payload.model_dump()).to_mongo()
        result = await self.items.insert_one(document)
        return QuizItemRead.model_validate({**document, "_id": result.inserted_id})

    async def update_item(self, item_id: str, payload: QuizItemInput) -> QuizItemRead:
        await self._check_article(payload.article_slug)
        document = await self.items.find_one_and_update(
            {"_id": _object_id(item_id)},
            {"$set": {**payload.model_dump(), "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            raise QuizItemNotFoundError("Claim was not found.")
        return QuizItemRead.model_validate(document)

    async def delete_item(self, item_id: str) -> bool:
        result = await self.items.delete_one({"_id": _object_id(item_id)})
        return bool(result.deleted_count)

    async def list_items(self) -> list[QuizItemRead]:
        cursor = self.items.find({}).sort([("created_at", DESCENDING)]).limit(500)
        return [QuizItemRead.model_validate(document) async for document in cursor]

    async def get_item(self, item_id: str) -> QuizItemRead | None:
        document = await self.items.find_one({"_id": _object_id(item_id)})
        return QuizItemRead.model_validate(document) if document else None

    async def _check_article(self, slug: str | None) -> None:
        if slug and not await self.database[ARTICLE_COLLECTION].count_documents(
            {"slug": slug, "status": ARTICLE_STATUS_PUBLISHED}, limit=1
        ):
            raise QuizArticleNotFoundError("Link a published article, or leave it empty.")

    # --- players -------------------------------------------------------------

    async def get_published(self, slug: str) -> QuizItemRead | None:
        document = await self.items.find_one({"slug": slug, "status": "published"})
        return QuizItemRead.model_validate(document) if document else None

    async def random_published(self, *, exclude_slug: str | None = None) -> QuizItemRead | None:
        """A random published claim, avoiding the one just played when possible.

        ponytail: loads every published slug and picks in Python; fine for
        hundreds of claims. Switch to a $sample aggregation if there are
        thousands.
        """
        slugs = [d["slug"] async for d in self.items.find({"status": "published"}, {"slug": 1})]
        choices = [slug for slug in slugs if slug != exclude_slug] or slugs
        return await self.get_published(random.choice(choices)) if choices else None

    async def linked_article(self, item: QuizItemRead) -> dict[str, Any] | None:
        if not item.article_slug:
            return None
        article = await self.database[ARTICLE_COLLECTION].find_one(
            {"slug": item.article_slug, "status": ARTICLE_STATUS_PUBLISHED}, {"title": 1, "slug": 1}
        )
        return {"title": article["title"], "url": f"/articles/{article['slug']}"} if article else None
