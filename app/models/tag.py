from dataclasses import asdict, dataclass
from typing import Any, Final


TAG_COLLECTION: Final = "tags"
TAG_DOCUMENT_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "slug",
)
TAG_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "slug",
)


@dataclass(slots=True)
class TagDocument:
    name: str
    slug: str

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.slug = self.slug.strip().lower()

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


def create_tag_document(
    *,
    name: str,
    slug: str,
) -> TagDocument:
    return TagDocument(
        name=name,
        slug=slug,
    )
