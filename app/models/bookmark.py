from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final


BOOKMARK_COLLECTION: Final = "bookmarks"


@dataclass(slots=True)
class BookmarkDocument:
    """A piece a member saved to read later. Unique per (user_id, article_id)."""

    user_id: str
    article_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)
