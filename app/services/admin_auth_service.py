from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config.settings import settings
from app.database.mongodb import get_database
from app.models.admin import (
    ADMIN_COLLECTION,
    create_admin_document,
    normalize_admin_role,
)
from app.schemas.admin import AdminCreate, AdminListResponse, AdminRead
from app.utils.security import create_access_token, hash_password, verify_password


class AdminAuthServiceError(Exception):
    pass


class AdminAlreadyExistsError(AdminAuthServiceError):
    pass


class AdminInvalidCredentialsError(AdminAuthServiceError):
    pass


class AdminNotFoundError(AdminAuthServiceError):
    pass


class AdminLastAdminError(AdminAuthServiceError):
    pass


class AdminSelfDeactivationError(AdminAuthServiceError):
    pass


class AdminAuthService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.database[ADMIN_COLLECTION]

    async def create_admin(self, payload: AdminCreate) -> AdminRead:
        admin_document = create_admin_document(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )

        try:
            result = await self.collection.insert_one(admin_document.to_mongo())
        except DuplicateKeyError as exc:
            raise AdminAlreadyExistsError(
                "An admin with this username already exists."
            ) from exc

        admin = await self.collection.find_one({"_id": result.inserted_id})
        if admin is None:
            raise AdminNotFoundError("Created admin could not be loaded.")

        return self._to_admin_read(admin)

    async def list_admins(self) -> AdminListResponse:
        cursor = self.collection.find({}).sort(
            [("created_at", DESCENDING), ("username", ASCENDING)]
        )
        admins = [self._to_admin_read(admin) async for admin in cursor]

        active_admins = sum(
            1 for admin in admins if admin.is_active and admin.role == "admin"
        )
        active_editors = sum(
            1 for admin in admins if admin.is_active and admin.role == "editor"
        )

        return AdminListResponse(
            items=admins,
            total=len(admins),
            active_admins=active_admins,
            active_editors=active_editors,
        )

    async def update_admin_role(self, admin_id: str, role: str) -> AdminRead:
        normalized_role = normalize_admin_role(role)
        object_id = self._to_object_id(admin_id)
        if object_id is None:
            raise AdminNotFoundError("Admin user was not found.")

        existing_admin = await self.collection.find_one({"_id": object_id})
        if existing_admin is None:
            raise AdminNotFoundError("Admin user was not found.")

        if (
            existing_admin.get("role") == "admin"
            and normalized_role != "admin"
            and existing_admin.get("is_active", True)
            and await self._active_admin_count() <= 1
        ):
            raise AdminLastAdminError("At least one active admin is required.")

        updated_admin = await self.collection.find_one_and_update(
            {"_id": object_id},
            {
                "$set": {
                    "role": normalized_role,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if updated_admin is None:
            raise AdminNotFoundError("Admin user was not found.")

        return self._to_admin_read(updated_admin)

    async def update_admin_password(self, admin_id: str, password: str) -> None:
        object_id = self._to_object_id(admin_id)
        if object_id is None:
            raise AdminNotFoundError("Admin user was not found.")

        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "password_hash": hash_password(password),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        if result.matched_count == 0:
            raise AdminNotFoundError("Admin user was not found.")

    async def update_admin_status(
        self,
        admin_id: str,
        *,
        is_active: bool,
        acting_admin_id: str,
    ) -> AdminRead:
        if not is_active and admin_id == acting_admin_id:
            raise AdminSelfDeactivationError("You cannot deactivate your own account.")

        object_id = self._to_object_id(admin_id)
        if object_id is None:
            raise AdminNotFoundError("Admin user was not found.")

        existing_admin = await self.collection.find_one({"_id": object_id})
        if existing_admin is None:
            raise AdminNotFoundError("Admin user was not found.")

        if (
            not is_active
            and existing_admin.get("role") == "admin"
            and existing_admin.get("is_active", True)
            and await self._active_admin_count() <= 1
        ):
            raise AdminLastAdminError("At least one active admin is required.")

        updated_admin = await self.collection.find_one_and_update(
            {"_id": object_id},
            {
                "$set": {
                    "is_active": is_active,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if updated_admin is None:
            raise AdminNotFoundError("Admin user was not found.")

        return self._to_admin_read(updated_admin)

    async def authenticate_admin(
        self,
        *,
        username: str,
        password: str,
    ) -> AdminRead:
        admin = await self.collection.find_one({"username": username.strip().lower()})
        if (
            admin is None
            or not admin.get("is_active", True)
            or not verify_password(password, str(admin.get("password_hash")))
        ):
            raise AdminInvalidCredentialsError("Invalid username or password.")

        return self._to_admin_read(admin)

    async def get_admin_by_id(self, admin_id: str) -> AdminRead | None:
        object_id = self._to_object_id(admin_id)
        if object_id is None:
            return None

        admin = await self.collection.find_one(
            {"_id": object_id, "is_active": {"$ne": False}}
        )
        if admin is None:
            return None

        return self._to_admin_read(admin)

    def create_login_token(self, admin: AdminRead) -> str:
        return create_access_token(
            subject=admin.id,
            secret_key=settings.auth_secret_key,
            expires_delta=timedelta(minutes=settings.auth_token_expire_minutes),
            claims={"role": admin.role, "username": admin.username},
        )

    def _to_object_id(self, value: str) -> ObjectId | None:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None

    async def _active_admin_count(self) -> int:
        return await self.collection.count_documents(
            {"role": "admin", "is_active": {"$ne": False}}
        )

    def _to_admin_read(self, admin: dict) -> AdminRead:
        admin.setdefault("is_active", True)
        return AdminRead.model_validate(admin)


def get_admin_auth_service(
    database: AsyncIOMotorDatabase | None = None,
) -> AdminAuthService:
    return AdminAuthService(database=database)
