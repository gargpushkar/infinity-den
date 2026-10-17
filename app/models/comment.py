from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal


COMMENT_COLLECTION: Final = "comments"

CommentStatus = Literal["published", "hidden"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class CommentDocument:
    """A member's comment on a published piece. Comments are flat: no replies."""

    article_id: str
    user_id: str
    author: str
    author_username: str
    body: str
    status: CommentStatus = "published"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)
