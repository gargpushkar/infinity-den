from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config.constants import (
    ARGUMENT_CLAIM_MAX_LENGTH,
    ARGUMENT_MAX_LENGTH,
    DEBATE_SIDE_LABELS,
    REBUTTAL_MAX_LENGTH,
    REBUTTAL_MIN_LENGTH,
)
from app.models.debate import ArgumentSide, ArgumentStatus, DebateStatus
from app.schemas.article import ArticleSource


def _strip(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


class DebateInput(BaseModel):
    """What an editor sets when writing a motion or changing its closing date."""

    motion: str = Field(min_length=10, max_length=200)
    intro: str | None = Field(default=None, max_length=1000)
    category_id: str | None = Field(default=None, max_length=120)
    closes_on: date
    status: DebateStatus = "draft"

    @field_validator("motion", "intro", "category_id", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        return _strip(value) or None


class DebateRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    motion: str
    slug: str
    intro: str | None = None
    category_id: str | None = None
    closes_on: str
    status: DebateStatus
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, value: Any) -> str:
        return str(value)


class ArgumentInput(BaseModel):
    """A member's argument: a side, a one-line claim, the case, and optional sources."""

    side: ArgumentSide
    claim: str = Field(min_length=10, max_length=ARGUMENT_CLAIM_MAX_LENGTH)
    body: str = Field(min_length=50, max_length=ARGUMENT_MAX_LENGTH)
    sources: list[ArticleSource] = Field(default_factory=list, max_length=10)

    @field_validator("claim", "body", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        return _strip(value)

    @field_validator("side", mode="before")
    @classmethod
    def known_side(cls, value: Any) -> Any:
        if value not in DEBATE_SIDE_LABELS:
            raise ValueError("Choose a side.")
        return value


class ArgumentRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    debate_id: str
    user_id: str
    author: str
    author_username: str
    side: ArgumentSide
    claim: str
    body: str
    sources: list[ArticleSource] = Field(default_factory=list)
    is_featured: bool = False
    status: ArgumentStatus = "published"
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None = None

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, value: Any) -> str:
        return str(value)


class AdminArgumentUpdate(BaseModel):
    is_featured: bool | None = None
    status: ArgumentStatus | None = None

    @model_validator(mode="after")
    def require_one_field(self) -> "AdminArgumentUpdate":
        if not self.model_fields_set:
            raise ValueError("Set is_featured or status.")
        return self


class RebuttalInput(BaseModel):
    body: str = Field(min_length=REBUTTAL_MIN_LENGTH, max_length=REBUTTAL_MAX_LENGTH)

    @field_validator("body", mode="before")
    @classmethod
    def strip_body(cls, value: Any) -> Any:
        return _strip(value)


class RebuttalRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    debate_id: str
    argument_id: str
    user_id: str
    author: str
    author_username: str
    body: str
    status: ArgumentStatus = "published"
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None = None

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, value: Any) -> str:
        return str(value)


class AdminRebuttalUpdate(BaseModel):
    status: ArgumentStatus
