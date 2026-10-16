from datetime import datetime
from math import ceil
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


BusinessSortField = Literal["name", "sort_order", "created_at", "updated_at"]
SortDirection = Literal["asc", "desc"]

# These values end up in href and src attributes on a public page, so only
# schemes that are safe to navigate to are accepted. A javascript: or data:
# URL saved here would otherwise execute for every visitor.
SAFE_URL_SCHEMES: tuple[str, ...] = ("http://", "https://")


def _as_optional_string(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()
    return value or None


def _validate_link(value: str | None, *, allow_relative: bool) -> str | None:
    clean_value = _as_optional_string(value)
    if clean_value is None:
        return None

    lowered = clean_value.lower()
    if lowered.startswith(SAFE_URL_SCHEMES):
        return clean_value
    if allow_relative and clean_value.startswith("/") and not clean_value.startswith("//"):
        return clean_value

    raise ValueError(
        "Links must start with http:// or https://"
        + (" or be a site-relative path beginning with /." if allow_relative else ".")
    )


class BusinessBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(
        min_length=2,
        max_length=120,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    tagline: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=480)
    logo: str | None = Field(default=None, max_length=500)
    website_url: str | None = Field(default=None, max_length=500)
    category_id: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    is_featured: bool = False
    sort_order: int = Field(default=0, ge=0, le=999)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("slug", "category_id", mode="before")
    @classmethod
    def normalize_slug(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() or None

        return value

    @field_validator("tagline", "description", "location", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        return _as_optional_string(value)

    @field_validator("sort_order", mode="before")
    @classmethod
    def default_sort_order(cls, value: Any) -> Any:
        if value is None or value == "":
            return 0

        return value

    @field_validator("website_url", mode="before")
    @classmethod
    def validate_website_url(cls, value: Any) -> str | None:
        return _validate_link(value, allow_relative=False)

    @field_validator("logo", mode="before")
    @classmethod
    def validate_logo(cls, value: Any) -> str | None:
        # Logos are commonly uploaded under /static, so relative paths are fine.
        return _validate_link(value, allow_relative=True)


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    tagline: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=480)
    logo: str | None = Field(default=None, max_length=500)
    website_url: str | None = Field(default=None, max_length=500)
    category_id: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    is_featured: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=999)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("slug", "category_id", mode="before")
    @classmethod
    def normalize_slug(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() or None

        return value

    @field_validator("tagline", "description", "location", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        return _as_optional_string(value)

    @field_validator("website_url", mode="before")
    @classmethod
    def validate_website_url(cls, value: Any) -> str | None:
        return _validate_link(value, allow_relative=False)

    @field_validator("logo", mode="before")
    @classmethod
    def validate_logo(cls, value: Any) -> str | None:
        return _validate_link(value, allow_relative=True)

    @model_validator(mode="after")
    def require_one_field(self) -> "BusinessUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one business field must be provided.")

        return self


class BusinessRead(BusinessBase):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str = Field(alias="_id")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("id", mode="before")
    @classmethod
    def stringify_database_id(cls, value: Any) -> str:
        return str(value)


class BusinessListResponse(BaseModel):
    items: list[BusinessRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    per_page: int = Field(ge=1, le=100)
    total_pages: int = Field(ge=0)
    sort_by: BusinessSortField
    sort_direction: SortDirection
    has_next: bool = False
    has_previous: bool = False
    next_page: int | None = Field(default=None, ge=1)
    previous_page: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def align_pagination(self) -> "BusinessListResponse":
        expected_total_pages = ceil(self.total / self.per_page) if self.total else 0
        if self.total_pages != expected_total_pages:
            self.total_pages = expected_total_pages

        self.has_next = self.page < expected_total_pages
        self.has_previous = self.page > 1 and expected_total_pages > 0
        self.next_page = self.page + 1 if self.has_next else None
        self.previous_page = self.page - 1 if self.has_previous else None

        return self


class BusinessQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=12, ge=1, le=100)
    search: str | None = Field(default=None, min_length=2, max_length=120)
    category_id: str | None = Field(default=None, max_length=120)
    is_featured: bool | None = None
    sort_by: BusinessSortField = "sort_order"
    sort_direction: SortDirection = "asc"

    @field_validator("search", "category_id", mode="before")
    @classmethod
    def normalize_search(cls, value: Any) -> str | None:
        return _as_optional_string(value)
