from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal


QUIZ_COLLECTION: Final = "quiz_items"

QuizStatus = Literal["draft", "published"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class QuizItemDocument:
    """One Fact or Fiction claim for the Curiosity Arcade."""

    claim: str
    slug: str
    is_true: bool
    explanation: str
    article_slug: str | None = None
    category_id: str | None = None
    status: QuizStatus = "draft"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)
