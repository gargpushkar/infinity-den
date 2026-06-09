from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.admin import AdminRole, normalize_admin_role


class AdminCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    role: AdminRole = "editor"

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: Any) -> str:
        return str(value or "").strip().lower()

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value: Any) -> AdminRole:
        return normalize_admin_role(str(value or "editor").strip().lower())


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: Any) -> str:
        return str(value or "").strip().lower()


class AdminRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    username: str
    role: AdminRole
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("id", mode="before")
    @classmethod
    def stringify_database_id(cls, value: Any) -> str:
        return str(value)

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value: Any) -> AdminRole:
        return normalize_admin_role(str(value))


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(ge=1)
    admin: AdminRead


class AdminPasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def prevent_reusing_password(self) -> "AdminPasswordChange":
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password.")

        return self


class AdminArticleFeatureUpdate(BaseModel):
    is_featured: bool


class AdminRoleUpdate(BaseModel):
    role: AdminRole

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value: Any) -> AdminRole:
        return normalize_admin_role(str(value or "").strip().lower())


class AdminPasswordUpdate(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class AdminStatusUpdate(BaseModel):
    is_active: bool


class AdminListResponse(BaseModel):
    items: list[AdminRead]
    total: int = Field(ge=0)
    active_admins: int = Field(ge=0)
    active_editors: int = Field(ge=0)
