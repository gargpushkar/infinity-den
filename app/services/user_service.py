from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION
from app.models.user import USER_COLLECTION, UserDocument
from app.schemas.user import MemberLogin, MemberProfileUpdate, MemberRead, MemberSignup
from app.utils.security import hash_password, verify_password


class UserServiceError(Exception):
    pass


class UsernameTakenError(UserServiceError):
    pass


class EmailTakenError(UserServiceError):
    pass


class InvalidCredentialsError(UserServiceError):
    pass


class UserService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.database[USER_COLLECTION]

    async def create_member(self, payload: MemberSignup) -> MemberRead:
        document = UserDocument(
            username=payload.username,
            display_name=payload.display_name,
            email=payload.email,
            password_hash=hash_password(payload.password),
        ).to_mongo()

        # The unique indexes are the source of truth; these checks only pick
        # the right message for the common case.
        if await self.collection.count_documents({"username": payload.username}, limit=1):
            raise UsernameTakenError("That username is taken.")
        if await self.collection.count_documents({"email": payload.email}, limit=1):
            raise EmailTakenError("An account with this email already exists.")

        try:
            result = await self.collection.insert_one(document)
        except DuplicateKeyError as exc:
            if "email" in str(exc):
                raise EmailTakenError("An account with this email already exists.") from exc
            raise UsernameTakenError("That username is taken.") from exc

        return MemberRead.model_validate({**document, "_id": result.inserted_id})

    async def authenticate(self, payload: MemberLogin) -> MemberRead:
        document = await self.collection.find_one({"email": payload.email})
        # Same error for unknown email, wrong password, or a disabled account,
        # so the form does not reveal which emails have accounts.
        if (
            document is None
            or not document.get("is_active", True)
            or not verify_password(payload.password, document.get("password_hash", ""))
        ):
            raise InvalidCredentialsError("Email or password is incorrect.")

        return MemberRead.model_validate(document)

    async def get_member_by_id(self, member_id: str) -> MemberRead | None:
        try:
            object_id = ObjectId(member_id)
        except (InvalidId, TypeError):
            return None

        document = await self.collection.find_one({"_id": object_id, "is_active": True})
        return MemberRead.model_validate(document) if document else None

    async def get_member_by_username(self, username: str) -> MemberRead | None:
        document = await self.collection.find_one(
            {"username": username.strip().lower(), "is_active": True}
        )
        return MemberRead.model_validate(document) if document else None

    async def update_profile(self, member_id: str, payload: MemberProfileUpdate) -> MemberRead:
        update: dict[str, Any] = {
            "display_name": payload.display_name,
            "bio": payload.bio or None,
            "updated_at": datetime.now(timezone.utc),
        }
        document = await self.collection.find_one_and_update(
            {"_id": ObjectId(member_id)},
            {"$set": update},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            raise UserServiceError("Member was not found.")

        # Pieces store the author's name for display; keep it current.
        await self.database[ARTICLE_COLLECTION].update_many(
            {"author_id": member_id},
            {"$set": {"author": payload.display_name}},
        )

        return MemberRead.model_validate(document)
