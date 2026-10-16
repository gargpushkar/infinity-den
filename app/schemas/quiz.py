from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.quiz import QuizStatus


class QuizItemInput(BaseModel):
    """What an editor sets on a Fact or Fiction claim."""

    claim: str = Field(min_length=10, max_length=200)
    is_true: bool
    explanation: str = Field(min_length=10, max_length=1000)
    # Optional, but encouraged: the deeper article the answer leads to.
    article_slug: str | None = Field(default=None, max_length=180)
    category_id: str | None = Field(default=None, max_length=120)
    status: QuizStatus = "draft"

    @field_validator("claim", "explanation", "article_slug", "category_id", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        return (value.strip() or None) if isinstance(value, str) else value


class QuizItemRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    claim: str
    slug: str
    is_true: bool
    explanation: str
    article_slug: str | None = None
    category_id: str | None = None
    status: QuizStatus
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, value: Any) -> str:
        return str(value)
