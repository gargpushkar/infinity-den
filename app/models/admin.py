from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Final, Literal, cast


AdminRole = Literal["admin", "editor"]

ADMIN_COLLECTION: Final = "admins"
ADMIN_ROLES: Final[tuple[AdminRole, ...]] = ("admin", "editor")
ADMIN_DOCUMENT_FIELDS: Final[tuple[str, ...]] = (
    "username",
    "password_hash",
    "role",
    "is_active",
    "created_at",
    "updated_at",
)
ADMIN_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "username",
    "password_hash",
    "role",
)


def normalize_admin_role(role: str) -> AdminRole:
    if role not in ADMIN_ROLES:
        valid_roles = ", ".join(ADMIN_ROLES)
        raise ValueError(
            f"Invalid admin role '{role}'. Expected one of: {valid_roles}."
        )

    return cast(AdminRole, role)


@dataclass(slots=True)
class AdminDocument:
    username: str
    password_hash: str
    role: AdminRole = "editor"
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.username = self.username.strip().lower()
        self.password_hash = self.password_hash.strip()
        self.role = normalize_admin_role(self.role)
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)


def create_admin_document(
    *,
    username: str,
    password_hash: str,
    role: str = "editor",
    is_active: bool = True,
) -> AdminDocument:
    return AdminDocument(
        username=username,
        password_hash=password_hash,
        role=normalize_admin_role(role),
        is_active=is_active,
    )
