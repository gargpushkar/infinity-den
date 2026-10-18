"""Confirming a member's email address.

New members can sign in and read straight away, but can't publish, respond,
comment, or report until they open the emailed link. The link is a signed
token naming the account and the address, valid for two days; nothing is
stored. Unconfirmed accounts are deleted after PENDING_ACCOUNT_DAYS by a TTL
index (app/database/indexes.py).
"""

import logging
from datetime import timedelta

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.config.settings import settings
from app.database.mongodb import get_database
from app.models.user import USER_COLLECTION
from app.schemas.user import MemberRead
from app.services.email_service import EmailError, send_email
from app.services.user_service import PENDING_ACCOUNT_DAYS
from app.utils.security import SecurityError, TokenValidationError, create_access_token, decode_access_token


logger = logging.getLogger(__name__)

CONFIRM_TOKEN_KIND = "email_confirm"
CONFIRM_LINK_HOURS = 48
# Clears both markers at once; also used when a password reset proves the inbox.
CONFIRMED = {"email_confirmed": True, "pending_expires_at": None}


class InvalidConfirmLinkError(Exception):
    pass


def create_confirm_token(member_id: str, email: str) -> str:
    return create_access_token(
        subject=member_id,
        secret_key=settings.auth_secret_key,
        expires_delta=timedelta(hours=CONFIRM_LINK_HOURS),
        claims={"kind": CONFIRM_TOKEN_KIND, "email": email},
    )


class EmailConfirmationService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.users = self.database[USER_COLLECTION]

    async def send_link(self, member: MemberRead, site_url: str) -> None:
        link = f"{site_url}/confirm-email?token={create_confirm_token(member.id, member.email)}"
        body = (
            f"Hi {member.display_name},\n\n"
            f"Welcome to {settings.app_name}. Confirm your email address to start taking part: "
            "writing, responding, commenting, and reporting.\n\n"
            f"{link}\n\n"
            f"The link works for {CONFIRM_LINK_HOURS} hours. Accounts that aren't confirmed "
            f"within {PENDING_ACCOUNT_DAYS} days are deleted.\n\n"
            f"If you didn't join {settings.app_name}, ignore this email and the account "
            "will be removed.\n\n"
            f"{settings.app_name}\n"
        )
        try:
            await send_email(member.email, f"Confirm your email for {settings.app_name}", body)
        except EmailError:
            logger.exception("Could not send an email confirmation link")

    async def confirm(self, token: str) -> MemberRead:
        """Mark the address confirmed. Opening a link twice is harmless."""
        try:
            claims = decode_access_token(token, settings.auth_secret_key)
            object_id = ObjectId(claims.get("sub"))
        except (TokenValidationError, SecurityError, InvalidId, TypeError) as exc:
            raise InvalidConfirmLinkError from exc
        if claims.get("kind") != CONFIRM_TOKEN_KIND:
            raise InvalidConfirmLinkError

        # Matching the email means a link for a replaced or changed address does nothing.
        member = await self.users.find_one_and_update(
            {"_id": object_id, "email": claims.get("email"), "is_active": True},
            {"$set": CONFIRMED},
            return_document=ReturnDocument.AFTER,
        )
        if member is None:
            raise InvalidConfirmLinkError
        return MemberRead.model_validate(member)
