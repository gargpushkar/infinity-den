from datetime import datetime
from math import ceil
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.article import ArticleRead, ArticleSortField, SortDirection


def _as_optional_string(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()
    return value or None


class SearchQueryParams(BaseModel):
    q: str = Field(min_length=2, max_length=120)
    category: str | None = Field(default=None, max_length=120)
    tag: str | None = Field(default=None, max_length=64)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=12, ge=1, le=100)
    sort_by: ArticleSortField = "published_at"
    sort_direction: SortDirection = "desc"

    @field_validator("q", mode="before")
    @classmethod
    def normalize_query(cls, value: Any) -> str:
        return _as_optional_string(value) or ""

    @field_validator("category", "tag", mode="before")
    @classmethod
    def normalize_optional_filters(cls, value: Any) -> str | None:
        return _as_optional_string(value)


class SearchArticleResult(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: str
    cover_image: str | None = None
    author: str
    category_id: str | None = None
    tags: list[str]
    published_at: datetime | None = None
    views: int = Field(default=0, ge=0)

    @classmethod
    def from_article(cls, article: ArticleRead) -> "SearchArticleResult":
        return cls(
            id=article.id,
            title=article.title,
            slug=article.slug,
            excerpt=article.excerpt,
            cover_image=article.cover_image,
            author=article.author,
            category_id=article.category_id,
            tags=article.tags,
            published_at=article.published_at,
            views=article.views,
        )


class SearchResponse(BaseModel):
    query: str
    category: str | None = None
    tag: str | None = None
    items: list[SearchArticleResult]
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
    def align_pagination(self) -> "SearchResponse":
        expected_total_pages = ceil(self.total / self.per_page) if self.total else 0
        if self.total_pages != expected_total_pages:
            self.total_pages = expected_total_pages

        self.has_next = self.page < expected_total_pages
        self.has_previous = self.page > 1 and expected_total_pages > 0
        self.next_page = self.page + 1 if self.has_next else None
        self.previous_page = self.page - 1 if self.has_previous else None

        return self
