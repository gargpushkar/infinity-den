from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal


REPORT_COLLECTION: Final = "reports"

ReportTarget = Literal["article", "response", "comment", "argument", "rebuttal", "stance"]
ReportStatus = Literal["open", "resolved", "dismissed"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ReportDocument:
    """A member flagging something for editors. One open report per member per item."""

    target_type: ReportTarget
    target_id: str
    reporter_id: str
    reason: str
    detail: str | None = None
    status: ReportStatus = "open"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None
    resolved_by: str | None = None

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)
