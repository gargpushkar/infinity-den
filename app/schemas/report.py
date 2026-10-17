from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config.constants import REPORT_DETAIL_MAX_LENGTH, REPORT_REASONS
from app.models.report import ReportStatus, ReportTarget


OBJECT_ID = r"^[0-9a-f]{24}$"


class ReportInput(BaseModel):
    target_type: ReportTarget
    target_id: str = Field(pattern=OBJECT_ID)
    reason: str
    detail: str | None = Field(default=None, max_length=REPORT_DETAIL_MAX_LENGTH)

    @field_validator("detail", mode="before")
    @classmethod
    def strip_detail(cls, value: Any) -> Any:
        return (value.strip() or None) if isinstance(value, str) else value

    @field_validator("reason")
    @classmethod
    def known_reason(cls, value: str) -> str:
        if value not in REPORT_REASONS:
            raise ValueError("Choose a reason.")
        return value

    @model_validator(mode="after")
    def explain_other(self) -> "ReportInput":
        if self.reason == "other" and not self.detail:
            raise ValueError("Tell us what is wrong.")
        return self


class ReportRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    target_type: ReportTarget
    target_id: str
    reporter_id: str
    reason: str
    detail: str | None = None
    status: ReportStatus
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, value: Any) -> str:
        return str(value)


class ReportAction(BaseModel):
    """An editor's decision on everything open about one item."""

    target_type: ReportTarget
    target_id: str = Field(pattern=OBJECT_ID)
    action: Literal["hide", "dismiss"]
