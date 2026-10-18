from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal


DELETION_REQUEST_COLLECTION: Final = "deletion_requests"
DeletionRequestStatus = Literal["pending", "deleted", "cancelled"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class DeletionRequestDocument:
    """A member asking for their account to be deleted. Editors do the deleting;
    once handled, only the email stays, as a record that the request was met."""

    user_id: str
    email: str
    username: str | None
    display_name: str | None
    status: DeletionRequestStatus = "pending"
    requested_at: datetime = field(default_factory=utc_now)
    handled_at: datetime | None = None
    handled_by: str | None = None

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)
