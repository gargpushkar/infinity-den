from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final


NEWSLETTER_SUBSCRIBER_COLLECTION: Final = "newsletter_subscribers"
NEWSLETTER_SUBSCRIBER_DOCUMENT_FIELDS: Final[tuple[str, ...]] = (
    "email",
    "created_at",
)
NEWSLETTER_SUBSCRIBER_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "email",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class NewsletterSubscriberDocument:
    email: str
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.email = self.email.strip().lower()

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


def create_newsletter_subscriber_document(
    *,
    email: str,
) -> NewsletterSubscriberDocument:
    return NewsletterSubscriberDocument(email=email)
