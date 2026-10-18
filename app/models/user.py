from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final


USER_COLLECTION: Final = "users"
USER_DOCUMENT_FIELDS: Final[tuple[str, ...]] = (
    "username",
    "display_name",
    "email",
    "password_hash",
    "bio",
    "is_active",
    "session_version",
    "email_confirmed",
    "pending_expires_at",
    "created_at",
    "updated_at",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class UserDocument:
    """A community member. Admins live in their own collection."""

    username: str
    display_name: str
    email: str
    password_hash: str
    bio: str | None = None
    is_active: bool = True
    # Raised by a password reset; sign-in cookies with an older number stop working.
    session_version: int = 0
    # Sign-ups start unconfirmed (False) until the emailed link is opened.
    # Accounts from before confirmation existed have no field and count as confirmed.
    email_confirmed: bool = True
    # Set while unconfirmed; a TTL index deletes the account when it passes.
    pending_expires_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.username = self.username.strip().lower()
        self.display_name = self.display_name.strip()
        self.email = self.email.strip().lower()
        self.bio = (self.bio or "").strip() or None

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)
