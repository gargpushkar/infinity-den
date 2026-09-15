from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Final


BUSINESS_COLLECTION: Final = "businesses"
BUSINESS_DOCUMENT_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "slug",
    "tagline",
    "description",
    "logo",
    "website_url",
    "category_id",
    "location",
    "is_featured",
    "sort_order",
    "created_at",
    "updated_at",
)
BUSINESS_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "slug",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class BusinessDocument:
    name: str
    slug: str
    tagline: str | None = None
    description: str | None = None
    logo: str | None = None
    website_url: str | None = None
    category_id: str | None = None
    location: str | None = None
    is_featured: bool = False
    sort_order: int = 0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.slug = self.slug.strip().lower()
        self.tagline = _clean_optional_text(self.tagline)
        self.description = _clean_optional_text(self.description)
        self.logo = _clean_optional_text(self.logo)
        self.website_url = _clean_optional_text(self.website_url)
        self.category_id = _clean_optional_text(self.category_id)
        self.location = _clean_optional_text(self.location)
        if self.sort_order < 0:
            raise ValueError("Business sort order cannot be negative.")

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


def create_business_document(
    *,
    name: str,
    slug: str,
    tagline: str | None = None,
    description: str | None = None,
    logo: str | None = None,
    website_url: str | None = None,
    category_id: str | None = None,
    location: str | None = None,
    is_featured: bool = False,
    sort_order: int = 0,
) -> BusinessDocument:
    now = utc_now()

    return BusinessDocument(
        name=name,
        slug=slug,
        tagline=tagline,
        description=description,
        logo=logo,
        website_url=website_url,
        category_id=category_id,
        location=location,
        is_featured=is_featured,
        sort_order=sort_order,
        created_at=now,
        updated_at=now,
    )


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    clean_value = value.strip()
    return clean_value or None
