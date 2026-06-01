from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal, cast

from app.config.constants import (
    ARTICLE_STATUS_ARCHIVED,
    ARTICLE_STATUS_DRAFT,
    ARTICLE_STATUS_PUBLISHED,
)


ArticleStatus = Literal["draft", "published", "archived"]

ARTICLE_COLLECTION: Final = "articles"
ARTICLE_STATUSES: Final[tuple[ArticleStatus, ...]] = (
    ARTICLE_STATUS_DRAFT,
    ARTICLE_STATUS_PUBLISHED,
    ARTICLE_STATUS_ARCHIVED,
)
ARTICLE_DOCUMENT_FIELDS: Final[tuple[str, ...]] = (
    "title",
    "slug",
    "excerpt",
    "content",
    "cover_image",
    "author",
    "category_id",
    "tags",
    "is_featured",
    "status",
    "seo_title",
    "seo_description",
    "created_at",
    "updated_at",
    "published_at",
    "views",
)
ARTICLE_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "title",
    "slug",
    "excerpt",
    "content",
    "author",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_article_status(status: str) -> ArticleStatus:
    if status not in ARTICLE_STATUSES:
        valid_statuses = ", ".join(ARTICLE_STATUSES)
        raise ValueError(
            f"Invalid article status '{status}'. Expected one of: {valid_statuses}."
        )

    return cast(ArticleStatus, status)


@dataclass(slots=True)
class ArticleDocument:
    title: str
    slug: str
    excerpt: str
    content: str
    author: str
    cover_image: str | None = None
    category_id: str | None = None
    tags: list[str] = field(default_factory=list)
    is_featured: bool = False
    status: ArticleStatus = ARTICLE_STATUS_DRAFT
    seo_title: str | None = None
    seo_description: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    published_at: datetime | None = None
    views: int = 0

    def __post_init__(self) -> None:
        self.status = normalize_article_status(self.status)
        self.tags = list(self.tags)
        if self.views < 0:
            raise ValueError("Article views cannot be negative.")

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


def create_article_document(
    *,
    title: str,
    slug: str,
    excerpt: str,
    content: str,
    author: str,
    cover_image: str | None = None,
    category_id: str | None = None,
    tags: list[str] | None = None,
    is_featured: bool = False,
    status: str = ARTICLE_STATUS_DRAFT,
    seo_title: str | None = None,
    seo_description: str | None = None,
    published_at: datetime | None = None,
) -> ArticleDocument:
    now = utc_now()

    return ArticleDocument(
        title=title,
        slug=slug,
        excerpt=excerpt,
        content=content,
        author=author,
        cover_image=cover_image,
        category_id=category_id,
        tags=list(tags or []),
        is_featured=is_featured,
        status=normalize_article_status(status),
        seo_title=seo_title,
        seo_description=seo_description,
        created_at=now,
        updated_at=now,
        published_at=published_at,
    )
