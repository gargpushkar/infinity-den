from dataclasses import asdict, dataclass
from typing import Any, Final


CATEGORY_COLLECTION: Final = "categories"
CATEGORY_DOCUMENT_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "slug",
    "description",
    "image",
)
CATEGORY_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "slug",
)


@dataclass(slots=True)
class CategoryDocument:
    name: str
    slug: str
    description: str | None = None
    image: str | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.slug = self.slug.strip().lower()
        self.description = _clean_optional_text(self.description)
        self.image = _clean_optional_text(self.image)

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


def create_category_document(
    *,
    name: str,
    slug: str,
    description: str | None = None,
    image: str | None = None,
) -> CategoryDocument:
    return CategoryDocument(
        name=name,
        slug=slug,
        description=description,
        image=image,
    )


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    clean_value = value.strip()
    return clean_value or None
