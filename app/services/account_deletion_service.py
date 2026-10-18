"""Deleting member accounts, which only editors do.

Members *request* deletion from their account page: the account is
deactivated at once (signed out everywhere, no sign-in, no public profile) and
the request waits in the deletion_requests collection. Editors delete from
/admin/deletions or scripts/delete_members.py, by request or by email address.

Deleting removes the account, the member's pieces (with their uploaded covers
and the comments and saves other people left on them), responses, debate
arguments, comments, and saved pieces. Reports the member filed stay, without the reporter; open
reports about the removed content are closed. The account goes last, so a
failure part-way leaves it in place to try again.
"""

import logging
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.settings import settings
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.bookmark import BOOKMARK_COLLECTION
from app.models.comment import COMMENT_COLLECTION
from app.models.debate import ARGUMENT_COLLECTION
from app.models.deletion_request import DELETION_REQUEST_COLLECTION, DeletionRequestDocument
from app.models.question import RESPONSE_COLLECTION
from app.models.report import REPORT_COLLECTION
from app.models.user import USER_COLLECTION
from app.services.cover_upload_service import discard_unused_cover
from app.services.email_service import EmailError, send_email
from app.utils.security import verify_password


logger = logging.getLogger(__name__)

# What members are promised: deleted within this many days of asking.
DELETION_DAYS = 30
MAX_BATCH = 100
# Stands in for the reporter on reports filed by a deleted member.
DELETED_REPORTER = "deleted-member"


class WrongPasswordError(Exception):
    pass


def parse_emails(text: str) -> list[str]:
    """Addresses separated by commas, spaces, or new lines; lowercased, no repeats."""
    seen: dict[str, None] = {}
    for item in re.split(r"[\s,;]+", text or ""):
        if item:
            seen.setdefault(item.strip().lower(), None)
    return list(seen)[:MAX_BATCH]


class AccountDeletionService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.users = self.database[USER_COLLECTION]
        self.requests = self.database[DELETION_REQUEST_COLLECTION]

    # --- members --------------------------------------------------------------

    async def request(self, member_id: str, password: str) -> dict[str, Any]:
        """Record a deletion request and deactivate the account. Returns the
        account, for the confirmation email."""
        try:
            object_id = ObjectId(member_id)
        except (InvalidId, TypeError) as exc:
            raise WrongPasswordError from exc
        account = await self.users.find_one({"_id": object_id})
        if account is None or not verify_password(password, account.get("password_hash", "")):
            raise WrongPasswordError

        now = datetime.now(timezone.utc)
        if not await self.requests.count_documents({"user_id": member_id, "status": "pending"}, limit=1):
            await self.requests.insert_one(DeletionRequestDocument(
                user_id=member_id, email=account["email"], username=account["username"],
                display_name=account["display_name"], requested_at=now,
            ).to_mongo())
        # Raising the session number signs the member out on every device.
        await self.users.update_one({"_id": object_id}, {"$set": {
            "is_active": False,
            "deletion_requested_at": now,
            "session_version": account.get("session_version", 0) + 1,
            "updated_at": now,
        }})
        return account

    # --- editors --------------------------------------------------------------

    async def pending_count(self) -> int:
        return await self.requests.count_documents({"status": "pending"})

    async def pending(self) -> list[dict[str, Any]]:
        """Waiting requests, oldest first, with the days left of the promise."""
        now = datetime.now(timezone.utc)
        items = []
        async for request in self.requests.find({"status": "pending"}).sort([("requested_at", 1)]).limit(500):
            requested_at = request["requested_at"]
            if requested_at.tzinfo is None:  # MongoDB hands datetimes back without a zone
                requested_at = requested_at.replace(tzinfo=timezone.utc)
            due = requested_at + timedelta(days=DELETION_DAYS)
            days_left = math.ceil((due - now).total_seconds() / 86400)  # asked today: 30, not 29
            items.append({**request, "id": str(request["_id"]), "days_left": days_left, "is_overdue": due <= now})
        return items

    async def cancel(self, request_id: str, editor: str) -> bool:
        """Withdraw a request (the member changed their mind) and reactivate the account."""
        try:
            object_id = ObjectId(request_id)
        except (InvalidId, TypeError):
            return False
        request = await self.requests.find_one({"_id": object_id, "status": "pending"})
        if request is None:
            return False
        now = datetime.now(timezone.utc)
        await self.requests.update_one({"_id": object_id}, {"$set": {"status": "cancelled", "handled_at": now, "handled_by": editor}})
        await self.users.update_one({"_id": ObjectId(request["user_id"])}, {"$set": {
            "is_active": True, "deletion_requested_at": None, "updated_at": now,
        }})
        return True

    async def preview(self, emails: list[str]) -> list[dict[str, Any]]:
        """What deleting these addresses would remove, without removing anything."""
        rows = []
        for email in emails:
            account = await self.users.find_one({"email": email})
            if account is None:
                rows.append({"email": email, "found": False})
                continue
            member_id = str(account["_id"])
            rows.append({
                "email": email,
                "found": True,
                "username": account["username"],
                "display_name": account["display_name"],
                "requested": bool(account.get("deletion_requested_at")),
                "pieces": await self.database[ARTICLE_COLLECTION].count_documents({"author_id": member_id}),
                "responses": await self.database[RESPONSE_COLLECTION].count_documents({"user_id": member_id}),
                "arguments": await self.database[ARGUMENT_COLLECTION].count_documents({"user_id": member_id}),
                "comments": await self.database[COMMENT_COLLECTION].count_documents({"user_id": member_id}),
                "saved": await self.database[BOOKMARK_COLLECTION].count_documents({"user_id": member_id}),
            })
        return rows

    async def delete_by_emails(self, emails: list[str], editor: str) -> list[dict[str, Any]]:
        """Delete every account with one of these addresses, and everything it wrote.

        Callers email the members who had asked (`requested`), with send_deleted_email.
        """
        results = []
        for email in emails:
            account = await self.users.find_one({"email": email})
            if account is None:
                results.append({"email": email, "deleted": False})
                continue
            member_id = str(account["_id"])
            await self._purge(account)
            now = datetime.now(timezone.utc)
            await self.requests.update_many(
                {"user_id": member_id, "status": "pending"},
                {"$set": {"status": "deleted", "handled_at": now, "handled_by": editor}},
            )
            # Every request for the account, cancelled ones too, keeps only the address.
            await self.requests.update_many({"user_id": member_id}, {"$set": {"username": None, "display_name": None}})
            results.append({"email": email, "deleted": True, "display_name": account["display_name"],
                            "requested": bool(account.get("deletion_requested_at"))})
        return results

    async def _purge(self, account: dict[str, Any]) -> None:
        db, member_id = self.database, str(account["_id"])
        pieces = [p async for p in db[ARTICLE_COLLECTION].find({"author_id": member_id}, {"_id": 1, "cover_image": 1})]
        piece_ids = [str(p["_id"]) for p in pieces]
        comment_ids = [str(c["_id"]) async for c in db[COMMENT_COLLECTION].find(
            {"$or": [{"user_id": member_id}, {"article_id": {"$in": piece_ids}}]}, {"_id": 1})]
        response_ids = [str(r["_id"]) async for r in db[RESPONSE_COLLECTION].find({"user_id": member_id}, {"_id": 1})]
        argument_ids = [str(a["_id"]) async for a in db[ARGUMENT_COLLECTION].find({"user_id": member_id}, {"_id": 1})]

        now = datetime.now(timezone.utc)
        await db[REPORT_COLLECTION].update_many(
            {"target_id": {"$in": piece_ids + comment_ids + response_ids + argument_ids}, "status": "open"},
            {"$set": {"status": "resolved", "resolved_at": now, "resolved_by": "account deleted", "updated_at": now}},
        )
        await db[REPORT_COLLECTION].update_many({"reporter_id": member_id}, {"$set": {"reporter_id": DELETED_REPORTER}})

        await db[COMMENT_COLLECTION].delete_many({"_id": {"$in": [ObjectId(i) for i in comment_ids]}})
        await db[RESPONSE_COLLECTION].delete_many({"user_id": member_id})
        await db[ARGUMENT_COLLECTION].delete_many({"user_id": member_id})
        await db[BOOKMARK_COLLECTION].delete_many({"$or": [{"user_id": member_id}, {"article_id": {"$in": piece_ids}}]})
        await db[ARTICLE_COLLECTION].delete_many({"author_id": member_id})
        for piece in pieces:
            await discard_unused_cover(db, piece.get("cover_image"))

        await self.users.delete_one({"_id": account["_id"]})


async def send_request_received(email: str, display_name: str) -> None:
    await _send(email, f"We've received your request to delete your {settings.app_name} account", (
        f"Hi {display_name},\n\n"
        f"We've received your request to delete your {settings.app_name} account. "
        "Your account is now deactivated, and it will be deleted, with everything you wrote "
        f"(pieces, drafts, responses, debate arguments, comments, and saved pieces), within {DELETION_DAYS} days.\n\n"
        f"If you didn't ask for this, or you've changed your mind, write to {settings.contact_email}.\n\n"
        f"{settings.app_name}\n"
    ))


async def send_deleted_email(email: str, display_name: str) -> None:
    await _send(email, f"Your {settings.app_name} account is deleted", (
        f"Hi {display_name},\n\n"
        f"As you asked, your {settings.app_name} account has been deleted, along with everything you wrote.\n\n"
        f"Thank you for being part of {settings.app_name}.\n\n{settings.app_name}\n"
    ))


async def _send(email: str, subject: str, body: str) -> None:
    try:
        await send_email(email, subject, body)
    except EmailError:
        logger.exception("Could not send an account deletion email")


async def send_deleted_emails(results: list[dict[str, Any]]) -> None:
    for result in results:
        if result.get("deleted") and result.get("requested"):
            await send_deleted_email(result["email"], result["display_name"])
