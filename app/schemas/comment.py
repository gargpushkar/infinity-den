from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config.constants import COMMENT_MAX_LENGTH
from app.models.comment import CommentStatus


class CommentInput(BaseModel):
    body: str = Field(min_length=2, max_length=COMMENT_MAX_LENGTH)

    @field_validator("body", mode="before")
    @classmethod
    def strip_body(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class CommentRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    article_id: str
    user_id: str
    author: str
    author_username: str
    body: str
    status: CommentStatus = "published"
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, value: Any) -> str:
        return str(value)
