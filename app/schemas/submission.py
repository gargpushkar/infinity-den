from datetime import datetime
from math import ceil
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config.constants import SUBMISSION_STATUS_NEW
from app.models.submission import SubmissionStatus, normalize_submission_status


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


class ArticleSubmissionUpdate(BaseModel):
    status: SubmissionStatus

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: Any) -> SubmissionStatus:
        return normalize_submission_status(str(value))


class ArticleSubmissionListResponse(BaseModel):
    items: list[ArticleSubmissionRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    per_page: int = Field(ge=1, le=100)
    total_pages: int = Field(ge=0)
    has_next: bool = False
    has_previous: bool = False
    next_page: int | None = Field(default=None, ge=1)
    previous_page: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def align_pagination(self) -> "ArticleSubmissionListResponse":
        expected_total_pages = ceil(self.total / self.per_page) if self.total else 0
        if self.total_pages != expected_total_pages:
            self.total_pages = expected_total_pages

        self.has_next = self.page < expected_total_pages
        self.has_previous = self.page > 1 and expected_total_pages > 0
        self.next_page = self.page + 1 if self.has_next else None
        self.previous_page = self.page - 1 if self.has_previous else None

        return self
