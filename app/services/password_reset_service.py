"""Password reset by emailed link.

The link carries a signed token (the same signing as sign-in tokens) that
expires after an hour and names a fingerprint of the current password hash.
Setting a new password changes the hash, so each link works once, with no
reset collection to store or clean up. A reset also raises the account's
session number, which signs out every other device.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.config.settings import settings
from app.database.mongodb import get_database
from app.models.user import USER_COLLECTION
from app.schemas.user import MemberRead
from app.services.email_confirmation_service import CONFIRMED
from app.services.email_service import EmailError, send_email
from app.utils.security import SecurityError, TokenValidationError, create_access_token, decode_access_token, hash_password


logger = logging.getLogger(__name__)

RESET_TOKEN_KIND = "password_reset"
RESET_LINK_MINUTES = 60


class InvalidResetLinkError(Exception):
    pass


def _fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def create_reset_token(member_id: str, password_hash: str) -> str:
    return create_access_token(
        subject=member_id,
        secret_key=settings.auth_secret_key,
        expires_delta=timedelta(minutes=RESET_LINK_MINUTES),
        claims={"kind": RESET_TOKEN_KIND, "pw": _fingerprint(password_hash)},
    )


class PasswordResetService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.users = self.database[USER_COLLECTION]

    async def send_reset_link(self, email: str, site_url: str) -> None:
        """Email a reset link if an active account uses this address; otherwise do nothing.

        Callers reply the same way either way, so the form never reveals who has an account.
        """
        member = await self.users.find_one({"email": email.strip().lower(), "is_active": True})
        if member is None:
            return
        link = f"{site_url}/reset-password?token={create_reset_token(str(member['_id']), member['password_hash'])}"
        body = (
            f"Hi {member['display_name']},\n\n"
            f"Someone asked to reset the password for your {settings.app_name} account. "
            f"To choose a new one, open this link within {RESET_LINK_MINUTES} minutes:\n\n"
            f"{link}\n\n"
            "The link works once. If you didn't ask for this, ignore this email: "
            "your password stays the same.\n\n"
            f"{settings.app_name}\n"
        )
        try:
            await send_email(member["email"], f"Reset your {settings.app_name} password", body)
        except EmailError:
            logger.exception("Could not send a password reset email")

    async def check_link(self, token: str) -> dict:
        """The account a valid, unused link belongs to. Raises InvalidResetLinkError."""
        try:
            claims = decode_access_token(token, settings.auth_secret_key)
            object_id = ObjectId(claims.get("sub"))
        except (TokenValidationError, SecurityError, InvalidId, TypeError) as exc:
            raise InvalidResetLinkError from exc
        if claims.get("kind") != RESET_TOKEN_KIND:
            raise InvalidResetLinkError
        member = await self.users.find_one({"_id": object_id, "is_active": True})
        if member is None or claims.get("pw") != _fingerprint(member["password_hash"]):
            raise InvalidResetLinkError  # unknown account, or the password already changed
        return member

    async def reset_password(self, token: str, new_password: str, site_url: str) -> MemberRead:
        member = await self.check_link(token)
        updated = await self.users.find_one_and_update(
            # Matching the old hash makes the link single-use even if it is opened twice at once.
            {"_id": member["_id"], "password_hash": member["password_hash"]},
            {"$set": {
                "password_hash": hash_password(new_password),
                "session_version": member.get("session_version", 0) + 1,
                "updated_at": datetime.now(timezone.utc),
                **CONFIRMED,  # opening the emailed link proves the address
            }},
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            raise InvalidResetLinkError

        body = (
            f"Hi {updated['display_name']},\n\n"
            f"The password for your {settings.app_name} account was just changed, "
            "and every other device was signed out.\n\n"
            "If this wasn't you, reset your password now and tell us:\n\n"
            f"{site_url}/forgot-password\n"
            f"{settings.contact_email}\n\n"
            f"{settings.app_name}\n"
        )
        try:
            await send_email(updated["email"], f"Your {settings.app_name} password was changed", body)
        except EmailError:
            logger.exception("Could not send a password-changed email")
        return MemberRead.model_validate(updated)
