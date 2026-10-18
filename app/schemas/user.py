import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.newsletter import EMAIL_PATTERN


USERNAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{1,28}[a-z0-9])$")
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128

# Usernames that would look official or collide with site paths.
RESERVED_USERNAMES = frozenset(
    {
        "admin", "administrator", "api", "account", "editor", "editors",
        "help", "infinity-den", "infinityden", "join", "login", "logout",
        "members", "moderator", "root", "staff", "static", "support", "system",
    }
)


def _clean_email(value: Any) -> str:
    return str(value or "").strip().lower()


class MemberSignup(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    display_name: str = Field(min_length=2, max_length=60)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: Any) -> str:
        return str(value or "").strip().lower()

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError(
                "Use 3-30 lowercase letters, numbers, hyphens, or underscores, "
                "starting and ending with a letter or number."
            )
        if value in RESERVED_USERNAMES:
            raise ValueError("That username is reserved.")

        return value

    @field_validator("display_name", mode="before")
    @classmethod
    def strip_display_name(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> str:
        return _clean_email(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")

        return value


class MemberLogin(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> str:
        return _clean_email(value)


class MemberProfileUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=60)
    bio: str | None = Field(default=None, max_length=300)

    @field_validator("display_name", "bio", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> str:
        return str(value or "").strip()


class MemberRead(BaseModel):
    """Full member record for the member themselves. Never render publicly."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    username: str
    display_name: str
    email: str
    bio: str | None = None
    is_active: bool = True
    session_version: int = 0
    email_confirmed: bool = True  # missing on accounts from before confirmation existed
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, value: Any) -> str:
        return str(value)


class MemberPublic(BaseModel):
    """What anyone may see about a member: no email, no password hash."""

    username: str
    display_name: str
    bio: str | None = None
    created_at: datetime


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> str:
        return _clean_email(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")
        return value


class PasswordResetInput(BaseModel):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
