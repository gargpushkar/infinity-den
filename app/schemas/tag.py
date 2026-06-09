from math import ceil
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TagSortField = Literal["name", "slug"]
SortDirection = Literal["asc", "desc"]


def _as_optional_string(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()
    return value or None


class TagBase(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    slug: str = Field(
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()

        return value


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=64)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()

        return value

    @model_validator(mode="after")
    def require_one_field(self) -> "TagUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one tag field must be provided.")

        return self


class TagRead(TagBase):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")

    @field_validator("id", mode="before")
    @classmethod
    def stringify_database_id(cls, value: Any) -> str:
        return str(value)


class TagListResponse(BaseModel):
    items: list[TagRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    per_page: int = Field(ge=1, le=100)
    total_pages: int = Field(ge=0)
    sort_by: TagSortField
    sort_direction: SortDirection
    has_next: bool = False
    has_previous: bool = False
    next_page: int | None = Field(default=None, ge=1)
    previous_page: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def align_pagination(self) -> "TagListResponse":
        expected_total_pages = ceil(self.total / self.per_page) if self.total else 0
        if self.total_pages != expected_total_pages:
            self.total_pages = expected_total_pages

        self.has_next = self.page < expected_total_pages
        self.has_previous = self.page > 1 and expected_total_pages > 0
        self.next_page = self.page + 1 if self.has_next else None
        self.previous_page = self.page - 1 if self.has_previous else None

        return self


class TagQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=12, ge=1, le=100)
    search: str | None = Field(default=None, min_length=2, max_length=64)
    sort_by: TagSortField = "name"
    sort_direction: SortDirection = "asc"

    @field_validator("search", mode="before")
    @classmethod
    def normalize_search(cls, value: Any) -> str | None:
        return _as_optional_string(value)
