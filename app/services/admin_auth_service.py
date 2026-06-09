from datetime import timedelta

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.config.settings import settings
from app.database.mongodb import get_database
from app.models.admin import ADMIN_COLLECTION, create_admin_document
from app.schemas.admin import AdminCreate, AdminRead
from app.utils.security import create_access_token, hash_password, verify_password


class AdminAuthServiceError(Exception):
    pass


class AdminAlreadyExistsError(AdminAuthServiceError):
    pass


class AdminInvalidCredentialsError(AdminAuthServiceError):
    pass


class AdminNotFoundError(AdminAuthServiceError):
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

        return AdminRead.model_validate(admin)

    async def authenticate_admin(
        self,
        *,
        username: str,
        password: str,
    ) -> AdminRead:
        admin = await self.collection.find_one({"username": username.strip().lower()})
        if admin is None or not verify_password(password, str(admin.get("password_hash"))):
            raise AdminInvalidCredentialsError("Invalid username or password.")

        return AdminRead.model_validate(admin)

    async def get_admin_by_id(self, admin_id: str) -> AdminRead | None:
        object_id = self._to_object_id(admin_id)
        if object_id is None:
            return None

        admin = await self.collection.find_one({"_id": object_id})
        if admin is None:
            return None

        return AdminRead.model_validate(admin)

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


def get_admin_auth_service(
    database: AsyncIOMotorDatabase | None = None,
) -> AdminAuthService:
    return AdminAuthService(database=database)
