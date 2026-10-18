"""The Debate Den: motions set by editors, members' arguments for and against,
and rebuttals of those arguments.

Arguments and rebuttals publish immediately (editors can hide them, and
feature arguments). A debate is open through its closing date, then stays
readable as an archive. Nothing is ordered by popularity: arguments are
featured first, then newest; rebuttals read oldest first, like a conversation.
A rebuttal answers one argument and can't be answered itself.
"""

import re
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database.mongodb import get_database
from app.models.debate import (
    ARGUMENT_COLLECTION,
    DEBATE_COLLECTION,
    REBUTTAL_COLLECTION,
    ArgumentDocument,
    DebateDocument,
    RebuttalDocument,
)
from app.schemas.debate import (
    AdminArgumentUpdate,
    AdminRebuttalUpdate,
    ArgumentInput,
    ArgumentRead,
    DebateInput,
    DebateRead,
    RebuttalInput,
    RebuttalRead,
)
from app.schemas.user import MemberRead


DEBATE_LIMIT = 200
ARGUMENT_LIMIT = 300
REBUTTAL_LIMIT = 2000


class DebateNotFoundError(Exception):
    pass


class DebateClosedError(Exception):
    pass


class OwnArgumentError(Exception):
    pass


def debate_slug(motion: str) -> str:
    words = re.sub(r"[^a-z0-9]+", "-", motion.lower()).strip("-")[:70].strip("-") or "debate"
    return f"{words}-{secrets.token_hex(2)}"


def is_open(debate: DebateRead, today: str) -> bool:
    return debate.status == "published" and debate.closes_on >= today


def _object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


class DebateService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.debates = self.database[DEBATE_COLLECTION]
        self.arguments = self.database[ARGUMENT_COLLECTION]
        self.rebuttals = self.database[REBUTTAL_COLLECTION]

    # --- editors -------------------------------------------------------------

    async def create_debate(self, payload: DebateInput) -> DebateRead:
        document = DebateDocument(
            motion=payload.motion,
            slug=debate_slug(payload.motion),
            closes_on=payload.closes_on.isoformat(),
            intro=payload.intro,
            category_id=payload.category_id,
            status=payload.status,
        ).to_mongo()
        result = await self.debates.insert_one(document)
        return DebateRead.model_validate({**document, "_id": result.inserted_id})

    async def update_debate(self, debate_id: str, payload: DebateInput) -> DebateRead:
        # The slug stays as created so links to the debate never break.
        document = await self.debates.find_one_and_update(
            {"_id": _object_id(debate_id)},
            {"$set": {
                "motion": payload.motion,
                "intro": payload.intro,
                "category_id": payload.category_id,
                "closes_on": payload.closes_on.isoformat(),
                "status": payload.status,
                "updated_at": datetime.now(timezone.utc),
            }},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            raise DebateNotFoundError("Debate was not found.")
        return DebateRead.model_validate(document)

    async def delete_debate(self, debate_id: str) -> bool:
        result = await self.debates.delete_one({"_id": _object_id(debate_id)})
        if result.deleted_count:
            await self.arguments.delete_many({"debate_id": debate_id})
            await self.rebuttals.delete_many({"debate_id": debate_id})
        return bool(result.deleted_count)

    async def list_debates(self) -> list[DebateRead]:
        cursor = self.debates.find({}).sort([("created_at", DESCENDING)]).limit(DEBATE_LIMIT)
        return [DebateRead.model_validate(document) async for document in cursor]

    async def get_debate(self, debate_id: str) -> DebateRead | None:
        document = await self.debates.find_one({"_id": _object_id(debate_id)})
        return DebateRead.model_validate(document) if document else None

    async def all_arguments(self, debate_id: str) -> list[ArgumentRead]:
        cursor = self.arguments.find({"debate_id": debate_id}).sort([("created_at", DESCENDING)])
        return [ArgumentRead.model_validate(document) async for document in cursor]

    async def moderate_argument(self, argument_id: str, payload: AdminArgumentUpdate) -> ArgumentRead:
        document = await self.arguments.find_one_and_update(
            {"_id": _object_id(argument_id)},
            {"$set": {**payload.model_dump(exclude_unset=True), "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            raise DebateNotFoundError("Argument was not found.")
        return ArgumentRead.model_validate(document)

    # --- readers -------------------------------------------------------------

    async def published_debates(self) -> list[DebateRead]:
        """Latest closing date first; the page splits them into open and closed."""
        cursor = self.debates.find({"status": "published"}).sort([("closes_on", DESCENDING)]).limit(DEBATE_LIMIT)
        return [DebateRead.model_validate(document) async for document in cursor]

    async def get_published_debate(self, slug: str) -> DebateRead | None:
        document = await self.debates.find_one({"slug": slug, "status": "published"})
        return DebateRead.model_validate(document) if document else None

    async def public_arguments(self, debate_id: str) -> list[ArgumentRead]:
        """Featured first, then newest. Hidden arguments never appear."""
        cursor = (
            self.arguments.find({"debate_id": debate_id, "status": "published"})
            .sort([("is_featured", DESCENDING), ("created_at", DESCENDING)])
            .limit(ARGUMENT_LIMIT)
        )
        return [ArgumentRead.model_validate(document) async for document in cursor]

    async def argument_counts(self, debate_ids: list[str]) -> dict[str, int]:
        pipeline = [
            {"$match": {"debate_id": {"$in": debate_ids}, "status": "published"}},
            {"$group": {"_id": "$debate_id", "count": {"$sum": 1}}},
        ]
        return {row["_id"]: row["count"] async for row in self.arguments.aggregate(pipeline)}

    # --- members -------------------------------------------------------------

    async def member_argument(self, debate_id: str, member: MemberRead) -> ArgumentRead | None:
        document = await self.arguments.find_one({"debate_id": debate_id, "user_id": member.id})
        return ArgumentRead.model_validate(document) if document else None

    async def save_argument(self, debate: DebateRead, member: MemberRead, payload: ArgumentInput, today: str) -> ArgumentRead:
        """Create or replace the member's one argument in this debate.

        Editing keeps the editors' decisions: hidden stays hidden, featured stays featured.
        """
        if not is_open(debate, today):
            raise DebateClosedError("This debate is closed.")

        now = datetime.now(timezone.utc)
        fields = {
            "side": payload.side,
            "claim": payload.claim,
            "body": payload.body,
            "sources": [source.model_dump() for source in payload.sources],
            "author": member.display_name,
            "updated_at": now,
        }
        existing = await self.arguments.find_one_and_update(
            {"debate_id": debate.id, "user_id": member.id},
            {"$set": fields},
            return_document=ReturnDocument.AFTER,
        )
        if existing is not None:
            return ArgumentRead.model_validate(existing)

        document = ArgumentDocument(
            debate_id=debate.id,
            user_id=member.id,
            author_username=member.username,
            **{key: value for key, value in fields.items() if key != "updated_at"},
        ).to_mongo()
        try:
            result = await self.arguments.insert_one(document)
        except DuplicateKeyError:
            # Two submissions raced; the unique index kept one. Edit that one.
            return await self.save_argument(debate, member, payload, today)
        return ArgumentRead.model_validate({**document, "_id": result.inserted_id})

    async def delete_argument(self, debate_id: str, member: MemberRead) -> bool:
        """Remove the member's argument, and the rebuttals of it with it."""
        deleted = await self.arguments.find_one_and_delete({"debate_id": debate_id, "user_id": member.id})
        if deleted is None:
            return False
        await self.rebuttals.delete_many({"argument_id": str(deleted["_id"])})
        return True

    # --- rebuttals -----------------------------------------------------------

    async def public_rebuttals(self, debate_id: str) -> dict[str, list[RebuttalRead]]:
        """Visible rebuttals by argument id, oldest first."""
        return await self._threads({"debate_id": debate_id, "status": "published"})

    async def member_rebuttals(self, debate_id: str, member: MemberRead) -> dict[str, RebuttalRead]:
        """The member's own rebuttals in this debate (hidden ones too), by argument id."""
        cursor = self.rebuttals.find({"debate_id": debate_id, "user_id": member.id})
        return {document["argument_id"]: RebuttalRead.model_validate(document) async for document in cursor}

    async def all_rebuttals(self, debate_id: str) -> dict[str, list[RebuttalRead]]:
        """Every rebuttal in the debate, hidden ones too, for editors."""
        return await self._threads({"debate_id": debate_id})

    async def _threads(self, query: dict) -> dict[str, list[RebuttalRead]]:
        cursor = self.rebuttals.find(query).sort([("created_at", 1)]).limit(REBUTTAL_LIMIT)
        threads: dict[str, list[RebuttalRead]] = {}
        async for document in cursor:
            rebuttal = RebuttalRead.model_validate(document)
            threads.setdefault(rebuttal.argument_id, []).append(rebuttal)
        return threads

    async def save_rebuttal(
        self, debate: DebateRead, argument_id: str, member: MemberRead, payload: RebuttalInput, today: str
    ) -> RebuttalRead:
        """Create or replace the member's one rebuttal of this argument. Hidden stays hidden."""
        if not is_open(debate, today):
            raise DebateClosedError("This debate is closed.")
        argument = await self.arguments.find_one(
            {"_id": _object_id(argument_id), "debate_id": debate.id, "status": "published"}
        )
        if argument is None:
            raise DebateNotFoundError("That argument is no longer here.")
        if argument["user_id"] == member.id:
            raise OwnArgumentError("You can't rebut your own argument. Edit it instead.")

        now = datetime.now(timezone.utc)
        existing = await self.rebuttals.find_one_and_update(
            {"argument_id": argument_id, "user_id": member.id},
            {"$set": {"body": payload.body, "author": member.display_name, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if existing is not None:
            return RebuttalRead.model_validate(existing)

        document = RebuttalDocument(
            debate_id=debate.id,
            argument_id=argument_id,
            user_id=member.id,
            author=member.display_name,
            author_username=member.username,
            body=payload.body,
        ).to_mongo()
        try:
            result = await self.rebuttals.insert_one(document)
        except DuplicateKeyError:
            # Two submissions raced; the unique index kept one. Edit that one.
            return await self.save_rebuttal(debate, argument_id, member, payload, today)
        return RebuttalRead.model_validate({**document, "_id": result.inserted_id})

    async def delete_rebuttal(self, argument_id: str, member: MemberRead) -> bool:
        result = await self.rebuttals.delete_one({"argument_id": argument_id, "user_id": member.id})
        return bool(result.deleted_count)

    async def moderate_rebuttal(self, rebuttal_id: str, payload: AdminRebuttalUpdate) -> RebuttalRead:
        document = await self.rebuttals.find_one_and_update(
            {"_id": _object_id(rebuttal_id)},
            {"$set": {"status": payload.status, "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            raise DebateNotFoundError("Rebuttal was not found.")
        return RebuttalRead.model_validate(document)
