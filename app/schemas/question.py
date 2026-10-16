from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config.constants import (
    RESPONSE_KIND_LABELS,
    RESPONSE_MAX_LENGTH,
    RESPONSE_SHORT_KIND,
    RESPONSE_SHORT_MAX_LENGTH,
)
from app.models.question import QuestionStatus, ResponseKind, ResponseStatus
from app.schemas.article import ArticleSource


def _strip(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


class QuestionInput(BaseModel):
    """What an editor sets when writing or rescheduling a question."""

    text: str = Field(min_length=10, max_length=280)
    intro: str | None = Field(default=None, max_length=600)
    category_id: str | None = Field(default=None, max_length=120)
    publish_date: date
    status: QuestionStatus = "draft"

    @field_validator("text", "intro", "category_id", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        return _strip(value) or None


class QuestionRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    text: str
    slug: str
    intro: str | None = None
    category_id: str | None = None
    publish_date: str
    status: QuestionStatus
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, value: Any) -> str:
        return str(value)


class ResponseInput(BaseModel):
    """A member's response. Length depends on the kind they choose."""

    kind: ResponseKind = "answer"
    body: str = Field(min_length=2, max_length=RESPONSE_MAX_LENGTH)
    sources: list[ArticleSource] = Field(default_factory=list, max_length=10)

    @field_validator("body", mode="before")
    @classmethod
    def strip_body(cls, value: Any) -> Any:
        return _strip(value)

    @field_validator("kind", mode="before")
    @classmethod
    def known_kind(cls, value: Any) -> Any:
        if value not in RESPONSE_KIND_LABELS:
            raise ValueError("Choose what kind of response this is.")
        return value

    @model_validator(mode="after")
    def kind_rules(self) -> "ResponseInput":
        if self.kind == RESPONSE_SHORT_KIND and len(self.body) > RESPONSE_SHORT_MAX_LENGTH:
            raise ValueError(
                f"A short thought is at most {RESPONSE_SHORT_MAX_LENGTH} characters. "
                "Choose “Answer” for something longer."
            )
        if self.kind == "researched" and not self.sources:
            raise ValueError("A researched answer needs at least one source.")
        return self


class ResponseRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    question_id: str
    user_id: str
    author: str
    author_username: str
    kind: ResponseKind
    body: str
    sources: list[ArticleSource] = Field(default_factory=list)
    is_featured: bool = False
    status: ResponseStatus = "published"
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, value: Any) -> str:
        return str(value)


class AdminResponseUpdate(BaseModel):
    is_featured: bool | None = None
    status: ResponseStatus | None = None

    @model_validator(mode="after")
    def require_one_field(self) -> "AdminResponseUpdate":
        if not self.model_fields_set:
            raise ValueError("Set is_featured or status.")
        return self
