"""Where readers stand on a motion before and after reading, and why.

A member says where they stand before reading, and again after. The "before"
locks once they give an "after", so nobody can rewrite where they started.
Only members who recorded both can count as changing their mind; moving is
measured on one line, Against -> Undecided -> For. Results, and the optional
notes, are public once the debate closes; editors see them live. A stance is
only ever shown with a name when its member wrote a note. There is no winner.
"""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config.constants import STANCE_LABELS, STANCE_SCALE
from app.database.mongodb import get_database
from app.models.debate import STANCE_COLLECTION, StanceDocument
from app.schemas.debate import AdminStanceUpdate, DebateRead, StanceAfterInput, StanceBeforeInput
from app.schemas.user import MemberRead
from app.services.debate_service import DebateClosedError, DebateNotFoundError, is_open


# ponytail: results are counted in Python from every stance in the debate;
# fine for thousands. Switch to an aggregation if debates get huge.
STANCE_LIMIT = 20_000


class StanceLockedError(Exception):
    pass


def _object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


class DebateStanceService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.stances = self.database[STANCE_COLLECTION]

    async def member_stance(self, debate_id: str, member: MemberRead) -> dict[str, Any] | None:
        return await self.stances.find_one({"debate_id": debate_id, "user_id": member.id})

    async def save_before(self, debate: DebateRead, member: MemberRead, payload: StanceBeforeInput, today: str) -> dict[str, Any]:
        if not is_open(debate, today):
            raise DebateClosedError("This debate is closed.")
        existing = await self.member_stance(debate.id, member)
        if existing is not None and existing.get("after"):
            raise StanceLockedError("You've already said where you stand after reading, so where you started is fixed.")
        return await self._save(debate, member, {"before": payload.stance})

    async def save_after(self, debate: DebateRead, member: MemberRead, payload: StanceAfterInput, today: str) -> dict[str, Any]:
        """Editing keeps an editor's decision: a hidden note stays hidden."""
        if not is_open(debate, today):
            raise DebateClosedError("This debate is closed.")
        return await self._save(debate, member, {"after": payload.stance, "note": payload.note})

    async def _save(self, debate: DebateRead, member: MemberRead, fields: dict[str, Any]) -> dict[str, Any]:
        existing = await self.stances.find_one_and_update(
            {"debate_id": debate.id, "user_id": member.id},
            {"$set": {**fields, "author": member.display_name, "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        if existing is not None:
            return existing
        document = StanceDocument(
            debate_id=debate.id, user_id=member.id, author=member.display_name, author_username=member.username, **fields
        ).to_mongo()
        try:
            result = await self.stances.insert_one(document)
        except DuplicateKeyError:
            # Two submissions raced; the unique index kept one. Update that one.
            return await self._save(debate, member, fields)
        return {**document, "_id": result.inserted_id}

    async def results(self, debate_id: str) -> dict[str, Any]:
        """Before and after counts, how many moved and which way, and the visible notes."""
        before = dict.fromkeys(STANCE_LABELS, 0)
        after = dict.fromkeys(STANCE_LABELS, 0)
        towards_for = towards_against = compared = 0
        changed_notes, held_notes = [], []
        cursor = self.stances.find({"debate_id": debate_id}).sort([("created_at", 1)]).limit(STANCE_LIMIT)
        async for stance in cursor:
            if stance.get("before"):
                before[stance["before"]] += 1
            if stance.get("after"):
                after[stance["after"]] += 1
            move = 0
            if stance.get("before") and stance.get("after"):
                move = STANCE_SCALE[stance["after"]] - STANCE_SCALE[stance["before"]]
                compared += 1
                towards_for += move > 0
                towards_against += move < 0
            if stance.get("note") and stance.get("after") and stance.get("status") == "published":
                (changed_notes if move else held_notes).append(stance)
        return {
            "before": _split(before),
            "after": _split(after),
            "changed": towards_for + towards_against,
            "compared": compared,  # members who said where they stood both before and after
            "towards_for": towards_for,
            "towards_against": towards_against,
            "notes": changed_notes + held_notes,
        }

    async def stance_counts(self, debate_ids: list[str]) -> dict[str, int]:
        """How many members have taken a stand in each debate."""
        pipeline = [{"$match": {"debate_id": {"$in": debate_ids}}}, {"$group": {"_id": "$debate_id", "count": {"$sum": 1}}}]
        return {row["_id"]: row["count"] async for row in self.stances.aggregate(pipeline)}

    async def all_notes(self, debate_id: str) -> list[dict[str, Any]]:
        """Every note in the debate, hidden ones too, for editors."""
        cursor = self.stances.find({"debate_id": debate_id}).sort([("created_at", 1)]).limit(STANCE_LIMIT)
        return [stance async for stance in cursor if stance.get("note")]

    async def moderate_note(self, stance_id: str, payload: AdminStanceUpdate) -> dict[str, Any]:
        document = await self.stances.find_one_and_update(
            {"_id": _object_id(stance_id)},
            {"$set": {"status": payload.status, "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            raise DebateNotFoundError("Note was not found.")
        return document


def _split(counts: dict[str, int]) -> dict[str, Any]:
    total = sum(counts.values())
    return {
        "total": total,
        "rows": [
            {"stance": key, "label": label, "count": counts[key], "percent": round(100 * counts[key] / total) if total else 0}
            for key, label in STANCE_LABELS.items()
        ],
    }
