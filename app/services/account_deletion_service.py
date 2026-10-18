"""Members deleting their own account, and everything they wrote.

Removed: the account, the member's pieces (with their uploaded covers and the
comments and saves other people left on them), responses, comments, and saved
pieces. Reports the member filed stay for editors, without the reporter;
open reports about the removed content are closed. The account goes last, so
a failure part-way leaves it in place to try again.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.settings import settings
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.bookmark import BOOKMARK_COLLECTION
from app.models.comment import COMMENT_COLLECTION
from app.models.question import RESPONSE_COLLECTION
from app.models.report import REPORT_COLLECTION
from app.models.user import USER_COLLECTION
from app.services.cover_upload_service import discard_unused_cover
from app.services.email_service import EmailError, send_email
from app.utils.security import verify_password


logger = logging.getLogger(__name__)

# Stands in for the reporter on reports filed by a deleted member.
DELETED_REPORTER = "deleted-member"


class WrongPasswordError(Exception):
    pass


class AccountDeletionService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()

    async def delete(self, member_id: str, password: str) -> dict[str, Any]:
        """Delete the account after checking its password. Returns the deleted
        account's email and name, for the goodbye email."""
        try:
            object_id = ObjectId(member_id)
        except (InvalidId, TypeError) as exc:
            raise WrongPasswordError from exc
        account = await self.database[USER_COLLECTION].find_one({"_id": object_id})
        if account is None or not verify_password(password, account.get("password_hash", "")):
            raise WrongPasswordError

        db = self.database
        pieces = [p async for p in db[ARTICLE_COLLECTION].find({"author_id": member_id}, {"_id": 1, "cover_image": 1})]
        piece_ids = [str(p["_id"]) for p in pieces]
        comment_ids = [str(c["_id"]) async for c in db[COMMENT_COLLECTION].find(
            {"$or": [{"user_id": member_id}, {"article_id": {"$in": piece_ids}}]}, {"_id": 1})]
        response_ids = [str(r["_id"]) async for r in db[RESPONSE_COLLECTION].find({"user_id": member_id}, {"_id": 1})]

        now = datetime.now(timezone.utc)
        await db[REPORT_COLLECTION].update_many(
            {"target_id": {"$in": piece_ids + comment_ids + response_ids}, "status": "open"},
            {"$set": {"status": "resolved", "resolved_at": now, "resolved_by": "account deleted", "updated_at": now}},
        )
        await db[REPORT_COLLECTION].update_many({"reporter_id": member_id}, {"$set": {"reporter_id": DELETED_REPORTER}})

        await db[COMMENT_COLLECTION].delete_many({"_id": {"$in": [ObjectId(i) for i in comment_ids]}})
        await db[RESPONSE_COLLECTION].delete_many({"user_id": member_id})
        await db[BOOKMARK_COLLECTION].delete_many({"$or": [{"user_id": member_id}, {"article_id": {"$in": piece_ids}}]})
        await db[ARTICLE_COLLECTION].delete_many({"author_id": member_id})
        for piece in pieces:
            await discard_unused_cover(db, piece.get("cover_image"))

        await db[USER_COLLECTION].delete_one({"_id": object_id})
        return {"email": account["email"], "display_name": account["display_name"]}


async def send_goodbye(email: str, display_name: str) -> None:
    body = (
        f"Hi {display_name},\n\n"
        f"Your {settings.app_name} account has been deleted, along with everything you wrote: "
        "pieces, drafts, responses, comments, and saved pieces.\n\n"
        f"If you didn't do this, write to {settings.contact_email} straight away.\n\n"
        f"Thank you for being part of {settings.app_name}.\n\n{settings.app_name}\n"
    )
    try:
        await send_email(email, f"Your {settings.app_name} account is deleted", body)
    except EmailError:
        logger.exception("Could not send an account-deleted email")
