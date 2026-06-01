from datetime import datetime
from math import ceil
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config.constants import ARTICLE_STATUS_DRAFT
from app.models.article import ArticleStatus, normalize_article_status


ArticleSortField = Literal[
    "published_at",
    "created_at",
    "updated_at",
    "views",
    "title",
]
SortDirection = Literal["asc", "desc"]


def _as_optional_string(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()
    return value or None


class ArticleBase(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    slug: str = Field(
        min_length=3,
        max_length=180,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    excerpt: str = Field(min_length=10, max_length=320)
    content: str = Field(min_length=1)
    cover_image: str | None = Field(default=None, max_length=500)
    author: str = Field(min_length=2, max_length=120)
    category_id: str | None = Field(default=None, max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=20)
    is_featured: bool = False
    status: ArticleStatus = ARTICLE_STATUS_DRAFT
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=160)
    published_at: datetime | None = None

    @field_validator("title", "excerpt", "content", "author", mode="before")
    @classmethod
    def strip_required_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()

        return value

    @field_validator(
        "cover_image",
        "category_id",
        "seo_title",
        "seo_description",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        return _as_optional_string(value)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: Any) -> ArticleStatus:
        return normalize_article_status(str(value))

    @field_validator("tags", mode="before")
    @classmethod
    def default_tags(cls, value: Any) -> Any:
        if value is None:
            return []

        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        normalized_tags: list[str] = []
        seen_tags: set[str] = set()

        for tag in tags:
            clean_tag = str(tag).strip()
            if not clean_tag:
                continue
            if len(clean_tag) > 64:
                raise ValueError("Article tags must be 64 characters or fewer.")
            if clean_tag.lower() in seen_tags:
                continue

            normalized_tags.append(clean_tag)
            seen_tags.add(clean_tag.lower())

        return normalized_tags


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    slug: str | None = Field(
        default=None,
        min_length=3,
        max_length=180,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    excerpt: str | None = Field(default=None, min_length=10, max_length=320)
    content: str | None = Field(default=None, min_length=1)
    cover_image: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, min_length=2, max_length=120)
    category_id: str | None = Field(default=None, max_length=120)
    tags: list[str] | None = Field(default=None, max_length=20)
    is_featured: bool | None = None
    status: ArticleStatus | None = None
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=160)
    published_at: datetime | None = None

    @field_validator("title", "excerpt", "content", "author", mode="before")
    @classmethod
    def strip_required_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()

        return value

    @field_validator(
        "cover_image",
        "category_id",
        "seo_title",
        "seo_description",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        return _as_optional_string(value)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: Any) -> ArticleStatus | None:
        if value is None:
            return None

        return normalize_article_status(str(value))

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None

        return ArticleBase.model_validate(
            {
                "title": "Placeholder title",
                "slug": "placeholder-title",
                "excerpt": "Placeholder excerpt",
                "content": "Placeholder content",
                "author": "Placeholder author",
                "tags": tags,
            }
        ).tags

    @model_validator(mode="after")
    def require_one_field(self) -> "ArticleUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one article field must be provided.")

        return self


class ArticleRead(ArticleBase):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime
    views: int = Field(default=0, ge=0)

    @field_validator("id", "category_id", mode="before")
    @classmethod
    def stringify_database_ids(cls, value: Any) -> str | None:
        return _as_optional_string(value)


class ArticleListResponse(BaseModel):
    items: list[ArticleRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    per_page: int = Field(ge=1, le=100)
    total_pages: int = Field(ge=0)
    sort_by: ArticleSortField
    sort_direction: SortDirection
    has_next: bool = False
    has_previous: bool = False
    next_page: int | None = Field(default=None, ge=1)
    previous_page: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def align_pagination(self) -> "ArticleListResponse":
        expected_total_pages = ceil(self.total / self.per_page) if self.total else 0
        if self.total_pages != expected_total_pages:
            self.total_pages = expected_total_pages

        self.has_next = self.page < expected_total_pages
        self.has_previous = self.page > 1 and expected_total_pages > 0
        self.next_page = self.page + 1 if self.has_next else None
        self.previous_page = self.page - 1 if self.has_previous else None

        return self


class ArticleQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=12, ge=1, le=100)
    status: ArticleStatus | None = None
    category_id: str | None = Field(default=None, max_length=120)
    tag: str | None = Field(default=None, max_length=64)
    is_featured: bool | None = None
    author: str | None = Field(default=None, max_length=120)
    published_from: datetime | None = None
    published_to: datetime | None = None
    search: str | None = Field(default=None, min_length=2, max_length=120)
    sort_by: ArticleSortField = "published_at"
    sort_direction: SortDirection = "desc"

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: Any) -> ArticleStatus | None:
        if value is None:
            return None

        return normalize_article_status(str(value))

    @field_validator("category_id", "tag", "author", "search", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        return _as_optional_string(value)

    @model_validator(mode="after")
    def validate_published_range(self) -> "ArticleQueryParams":
        if (
            self.published_from is not None
            and self.published_to is not None
            and self.published_from > self.published_to
        ):
            raise ValueError("published_from must be before published_to.")

        return self
