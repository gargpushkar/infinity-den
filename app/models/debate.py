from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal


DEBATE_COLLECTION: Final = "debates"
ARGUMENT_COLLECTION: Final = "arguments"
REBUTTAL_COLLECTION: Final = "rebuttals"
RATING_COLLECTION: Final = "argument_ratings"

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
    edited_at: datetime | None = None  # set when the author changes the words

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RebuttalDocument:
    """A short reply to one argument. One per member per argument, and no replies to replies."""

    debate_id: str
    argument_id: str
    user_id: str
    author: str
    author_username: str
    body: str
    status: ArgumentStatus = "published"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    edited_at: datetime | None = None  # set when the author changes the words

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RatingDocument:
    """One member's 1-5 scores for one argument. Only averages are ever shown."""

    debate_id: str
    argument_id: str
    user_id: str
    clarity: int
    evidence: int
    reasoning: int
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)
