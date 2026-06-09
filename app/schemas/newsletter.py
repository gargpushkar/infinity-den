import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


class NewsletterSubscriptionCreate(BaseModel):
    email: str = Field(min_length=5, max_length=254)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> str:
        return str(value or "").strip().lower()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")

        return value


class NewsletterSubscriberRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    email: str
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def stringify_database_id(cls, value: Any) -> str:
        return str(value)


class NewsletterSubscriptionResponse(BaseModel):
    subscriber: NewsletterSubscriberRead
    message: str
