from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal


DEBATE_COLLECTION: Final = "debates"
ARGUMENT_COLLECTION: Final = "arguments"

DebateStatus = Literal["draft", "published"]
ArgumentSide = Literal["for", "against"]
ArgumentStatus = Literal["published", "hidden"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class DebateDocument:
    """A motion set by editors. Open while published, through closes_on
    ("YYYY-MM-DD" in the site timezone); after that it is read-only."""

    motion: str
    slug: str
    closes_on: str
    intro: str | None = None
    category_id: str | None = None
    status: DebateStatus = "draft"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ArgumentDocument:
    """A member's case for or against a motion. One per member per debate."""

    debate_id: str
    user_id: str
    author: str
    author_username: str
    side: ArgumentSide
    claim: str
    body: str
    sources: list[dict[str, str]] = field(default_factory=list)
    is_featured: bool = False
    status: ArgumentStatus = "published"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)
