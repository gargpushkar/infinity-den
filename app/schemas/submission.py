import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config.constants import SUBMISSION_STATUS_NEW
from app.models.submission import SubmissionStatus, normalize_submission_status


EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


class ArticleSubmissionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    topic: str = Field(min_length=5, max_length=160)
    content_idea: str = Field(min_length=20, max_length=2000)

    @field_validator("name", "topic", "content_idea", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> str:
        return str(value or "").strip()

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


class ArticleSubmissionRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    name: str
    email: str
    topic: str
    content_idea: str
    status: SubmissionStatus = SUBMISSION_STATUS_NEW
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def stringify_database_id(cls, value: Any) -> str:
        return str(value)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: Any) -> SubmissionStatus:
        return normalize_submission_status(str(value))


class ArticleSubmissionResponse(BaseModel):
    submission: ArticleSubmissionRead
    message: str
