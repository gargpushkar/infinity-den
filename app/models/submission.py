from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal, cast

from app.config.constants import (
    SUBMISSION_STATUS_ACCEPTED,
    SUBMISSION_STATUS_NEW,
    SUBMISSION_STATUS_REJECTED,
    SUBMISSION_STATUS_REVIEWING,
)


SubmissionStatus = Literal["new", "reviewing", "accepted", "rejected"]

ARTICLE_SUBMISSION_COLLECTION: Final = "article_submissions"
SUBMISSION_STATUSES: Final[tuple[SubmissionStatus, ...]] = (
    SUBMISSION_STATUS_NEW,
    SUBMISSION_STATUS_REVIEWING,
    SUBMISSION_STATUS_ACCEPTED,
    SUBMISSION_STATUS_REJECTED,
)
ARTICLE_SUBMISSION_DOCUMENT_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "email",
    "topic",
    "content_idea",
    "status",
    "created_at",
)
ARTICLE_SUBMISSION_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "email",
    "topic",
    "content_idea",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_submission_status(status: str) -> SubmissionStatus:
    if status not in SUBMISSION_STATUSES:
        valid_statuses = ", ".join(SUBMISSION_STATUSES)
        raise ValueError(
            f"Invalid submission status '{status}'. Expected one of: {valid_statuses}."
        )

    return cast(SubmissionStatus, status)


@dataclass(slots=True)
class ArticleSubmissionDocument:
    name: str
    email: str
    topic: str
    content_idea: str
    status: SubmissionStatus = SUBMISSION_STATUS_NEW
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.email = self.email.strip().lower()
        self.topic = self.topic.strip()
        self.content_idea = self.content_idea.strip()
        self.status = normalize_submission_status(self.status)

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


def create_article_submission_document(
    *,
    name: str,
    email: str,
    topic: str,
    content_idea: str,
    status: str = SUBMISSION_STATUS_NEW,
) -> ArticleSubmissionDocument:
    return ArticleSubmissionDocument(
        name=name,
        email=email,
        topic=topic,
        content_idea=content_idea,
        status=normalize_submission_status(status),
    )
