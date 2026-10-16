from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal


QUESTION_COLLECTION: Final = "daily_questions"
RESPONSE_COLLECTION: Final = "responses"

QuestionStatus = Literal["draft", "published"]
ResponseKind = Literal["thought", "answer", "story", "researched"]
ResponseStatus = Literal["published", "hidden"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class QuestionDocument:
    """One curated question. publish_date is "YYYY-MM-DD" in the site timezone."""

    text: str
    slug: str
    publish_date: str
    intro: str | None = None
    category_id: str | None = None
    status: QuestionStatus = "draft"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ResponseDocument:
    """A member's answer to a question. One per member per question."""

    question_id: str
    user_id: str
    author: str
    author_username: str
    kind: ResponseKind
    body: str
    sources: list[dict[str, str]] = field(default_factory=list)
    is_featured: bool = False
    status: ResponseStatus = "published"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)
