from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal, cast

from app.config.constants import (
    ARTICLE_FORMAT_ARTICLE,
    ARTICLE_FORMAT_EXPERIENCE,
    ARTICLE_FORMAT_PERSPECTIVE,
    ARTICLE_STATUS_ARCHIVED,
    ARTICLE_STATUS_DRAFT,
    ARTICLE_STATUS_PUBLISHED,
)


ArticleStatus = Literal["draft", "published", "archived"]
ArticleFormat = Literal["article", "experience", "perspective"]

ARTICLE_COLLECTION: Final = "articles"
ARTICLE_STATUSES: Final[tuple[ArticleStatus, ...]] = (
    ARTICLE_STATUS_DRAFT,
    ARTICLE_STATUS_PUBLISHED,
    ARTICLE_STATUS_ARCHIVED,
)
ARTICLE_FORMATS: Final[tuple[ArticleFormat, ...]] = (
    ARTICLE_FORMAT_ARTICLE,
    ARTICLE_FORMAT_EXPERIENCE,
    ARTICLE_FORMAT_PERSPECTIVE,
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
    "article_format",
    "is_editors_pick",
    "is_speculative",
    "sources",
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


def missing_required_sources(
    *,
    article_format: str,
    status: str,
    sources: list[Any] | None,
) -> bool:
    """Researched articles need at least one source before they go live.

    Drafts are exempt so writers can save work in progress.
    """
    return (
        article_format == ARTICLE_FORMAT_ARTICLE
        and status == ARTICLE_STATUS_PUBLISHED
        and not sources
    )


def normalize_article_status(status: str) -> ArticleStatus:
    if status not in ARTICLE_STATUSES:
        valid_statuses = ", ".join(ARTICLE_STATUSES)
        raise ValueError(
            f"Invalid article status '{status}'. Expected one of: {valid_statuses}."
        )

    return cast(ArticleStatus, status)


def normalize_article_format(article_format: str) -> ArticleFormat:
    if article_format not in ARTICLE_FORMATS:
        valid_formats = ", ".join(ARTICLE_FORMATS)
        raise ValueError(
            f"Invalid article format '{article_format}'. "
            f"Expected one of: {valid_formats}."
        )

    return cast(ArticleFormat, article_format)


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
    article_format: ArticleFormat = ARTICLE_FORMAT_ARTICLE
    is_editors_pick: bool = False
    is_speculative: bool = False
    sources: list[dict[str, str]] = field(default_factory=list)
    status: ArticleStatus = ARTICLE_STATUS_DRAFT
    seo_title: str | None = None
    seo_description: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    published_at: datetime | None = None
    views: int = 0

    def __post_init__(self) -> None:
        self.status = normalize_article_status(self.status)
        self.article_format = normalize_article_format(self.article_format)
        self.tags = list(self.tags)
        self.sources = list(self.sources)
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
    article_format: str = ARTICLE_FORMAT_ARTICLE,
    is_editors_pick: bool = False,
    is_speculative: bool = False,
    sources: list[dict[str, str]] | None = None,
    status: str = ARTICLE_STATUS_DRAFT,
    seo_title: str | None = None,
    seo_description: str | None = None,
    published_at: datetime | None = None,
    views: int = 0,
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
        article_format=normalize_article_format(article_format),
        is_editors_pick=is_editors_pick,
        is_speculative=is_speculative,
        sources=list(sources or []),
        status=normalize_article_status(status),
        seo_title=seo_title,
        seo_description=seo_description,
        created_at=now,
        updated_at=now,
        published_at=published_at,
        views=views,
    )
