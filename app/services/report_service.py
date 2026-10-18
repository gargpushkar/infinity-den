"""Reports: members flag articles, responses, comments, arguments, rebuttals, and
debate notes ("why I changed my mind"); editors hide or dismiss.

Nothing changes publicly until an editor acts. Hiding a response or comment
sets it to "hidden"; hiding an article archives it, so it leaves the site but
stays in admin.
"""

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.config.constants import ARTICLE_STATUS_PUBLISHED, REPORT_REASONS
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.comment import COMMENT_COLLECTION
from app.models.debate import ARGUMENT_COLLECTION, DEBATE_COLLECTION, REBUTTAL_COLLECTION, STANCE_COLLECTION
from app.models.question import QUESTION_COLLECTION, RESPONSE_COLLECTION
from app.models.report import REPORT_COLLECTION, ReportDocument
from app.schemas.admin import AdminRead
from app.schemas.report import ReportAction, ReportInput, ReportRead
from app.schemas.user import MemberRead


# ponytail: the queue groups in Python and looks each item up; fine for a small
# community. Move grouping to an aggregation if open reports reach thousands.
QUEUE_LIMIT = 500
HANDLED_LIMIT = 20
TARGET_LABELS = {"article": "Piece", "response": "Response", "comment": "Comment", "argument": "Argument", "rebuttal": "Rebuttal", "stance": "Debate note"}
HIDDEN_STATUS = {"article": "archived", "response": "hidden", "comment": "hidden", "argument": "hidden", "rebuttal": "hidden", "stance": "hidden"}
COLLECTIONS = {
    "article": ARTICLE_COLLECTION,
    "response": RESPONSE_COLLECTION,
    "comment": COMMENT_COLLECTION,
    "argument": ARGUMENT_COLLECTION,
    "rebuttal": REBUTTAL_COLLECTION,
    "stance": STANCE_COLLECTION,  # hiding one hides its note; the stance still counts
}
# Where a response, comment, argument, or rebuttal lives: (parent id field, parent collection, URL base).
PARENTS = {
    "response": ("question_id", QUESTION_COLLECTION, "/questions"),
    "comment": ("article_id", ARTICLE_COLLECTION, "/articles"),
    "argument": ("debate_id", DEBATE_COLLECTION, "/debates"),
    "rebuttal": ("debate_id", DEBATE_COLLECTION, "/debates"),
    "stance": ("debate_id", DEBATE_COLLECTION, "/debates"),
}


class ReportError(Exception):
    pass


class ReportTargetNotFoundError(ReportError):
    pass


class OwnContentError(ReportError):
    pass


def _object_id(value: str | None) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def _excerpt(text: str, limit: int = 280) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


class ReportService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.reports = self.database[REPORT_COLLECTION]

    async def target(self, target_type: str, target_id: str) -> dict[str, Any] | None:
        """What is being reported: a short preview, its owner, and where it lives."""
        document = await self.database[COLLECTIONS[target_type]].find_one({"_id": _object_id(target_id)})
        if document is None:
            return None

        if target_type == "article":
            text, author, owner_id = document.get("title", ""), document.get("author", ""), document.get("author_id")
            url, is_visible = f"/articles/{document.get('slug')}", document.get("status") == ARTICLE_STATUS_PUBLISHED
        else:
            parent_key, parent_collection, base = PARENTS[target_type]
            parent = await self.database[parent_collection].find_one({"_id": _object_id(document.get(parent_key))}, {"slug": 1})
            url = f"{base}/{parent['slug']}#{target_type}-{target_id}" if parent else ""
            if target_type == "argument":
                text = f"{document['claim']}: {document.get('body', '')}"
            else:
                text = document.get("note" if target_type == "stance" else "body") or ""
            author, owner_id = document.get("author", ""), document.get("user_id")
            is_visible = document.get("status") == "published" and bool(text)

        return {
            "type": target_type,
            "id": target_id,
            "label": TARGET_LABELS[target_type],
            "text": _excerpt(text),
            "author": author,
            "owner_id": owner_id,
            "url": url,
            "is_visible": is_visible,
        }

    # --- members -------------------------------------------------------------

    async def submit(self, member: MemberRead, payload: ReportInput) -> ReportRead:
        target = await self.target(payload.target_type, payload.target_id)
        if target is None or not target["is_visible"]:
            raise ReportTargetNotFoundError("That item is no longer on the site.")
        if target["owner_id"] == member.id:
            raise OwnContentError("You can't report your own contribution.")

        now = datetime.now(timezone.utc)
        key = {"target_type": payload.target_type, "target_id": payload.target_id, "reporter_id": member.id, "status": "open"}
        # Reporting the same item again updates the member's open report.
        existing = await self.reports.find_one_and_update(
            key,
            {"$set": {"reason": payload.reason, "detail": payload.detail, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if existing is not None:
            return ReportRead.model_validate(existing)

        document = ReportDocument(
            target_type=payload.target_type,
            target_id=payload.target_id,
            reporter_id=member.id,
            reason=payload.reason,
            detail=payload.detail,
        ).to_mongo()
        result = await self.reports.insert_one(document)
        return ReportRead.model_validate({**document, "_id": result.inserted_id})

    # --- editors -------------------------------------------------------------

    async def open_count(self) -> int:
        return await self.reports.count_documents({"status": "open"})

    async def queue(self) -> list[dict[str, Any]]:
        """Open reports grouped by item: most-reported first, then oldest."""
        cursor = self.reports.find({"status": "open"}).sort([("created_at", ASCENDING)]).limit(QUEUE_LIMIT)
        groups: dict[tuple[str, str], list[ReportRead]] = {}
        async for document in cursor:
            report = ReportRead.model_validate(document)
            groups.setdefault((report.target_type, report.target_id), []).append(report)

        items = []
        for (target_type, target_id), reports in groups.items():
            reasons = Counter(REPORT_REASONS.get(report.reason, report.reason) for report in reports)
            items.append(
                {
                    "target_type": target_type,
                    "target_id": target_id,
                    "target": await self.target(target_type, target_id),
                    "count": len(reports),
                    "reasons": reasons.most_common(),
                    "details": [report.detail for report in reports if report.detail],
                    "first_reported": reports[0].created_at,
                }
            )
        return sorted(items, key=lambda item: (-item["count"], item["first_reported"]))

    async def recently_handled(self) -> list[dict[str, Any]]:
        cursor = (
            self.reports.find({"status": {"$in": ["resolved", "dismissed"]}})
            .sort([("resolved_at", DESCENDING)])
            .limit(HANDLED_LIMIT)
        )
        handled = []
        async for document in cursor:
            report = ReportRead.model_validate(document)
            handled.append(
                {
                    "report": report,
                    "reason": REPORT_REASONS.get(report.reason, report.reason),
                    "target": await self.target(report.target_type, report.target_id),
                    "label": TARGET_LABELS[report.target_type],
                }
            )
        return handled

    async def act(self, payload: ReportAction, admin: AdminRead) -> int:
        """Hide the item or dismiss its reports; closes every open report on it."""
        now = datetime.now(timezone.utc)
        if payload.action == "hide":
            await self.database[COLLECTIONS[payload.target_type]].update_one(
                {"_id": _object_id(payload.target_id)},
                {"$set": {"status": HIDDEN_STATUS[payload.target_type], "updated_at": now}},
            )
        result = await self.reports.update_many(
            {"target_type": payload.target_type, "target_id": payload.target_id, "status": "open"},
            {
                "$set": {
                    "status": "resolved" if payload.action == "hide" else "dismissed",
                    "resolved_at": now,
                    "resolved_by": admin.username,
                    "updated_at": now,
                }
            },
        )
        return result.modified_count
