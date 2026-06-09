import asyncio
import getpass
import sys
from pathlib import Path

from pydantic import ValidationError
from pymongo.errors import PyMongoError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.schemas.admin import AdminCreate
from app.services.admin_auth_service import (
    AdminAlreadyExistsError,
    AdminAuthService,
)


def prompt_admin_payload() -> AdminCreate:
    print("Create an Infinity Den admin user")
    print("---------------------------------")

    username = input("Username: ").strip()
    role = input("Role [admin/editor] (default: admin): ").strip().lower() or "admin"
    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm password: ")

    if password != confirm_password:
        raise ValueError("Passwords do not match.")

    return AdminCreate(username=username, password=password, role=role)


async def create_admin() -> int:
    try:
        payload = prompt_admin_payload()
    except (ValidationError, ValueError) as exc:
        print(f"Invalid admin details: {exc}", file=sys.stderr)
        return 1

    try:
        await connect_to_mongo()
        admin = await AdminAuthService(get_database()).create_admin(payload)
    except AdminAlreadyExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except PyMongoError as exc:
        print(f"MongoDB error: {exc}", file=sys.stderr)
        return 1
    finally:
        await close_mongo_connection()

    print(f"Created admin user '{admin.username}' with role '{admin.role}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(create_admin()))
