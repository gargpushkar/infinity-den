"""Create the six launch rooms in a fresh database. Safe for production.

Creates only rooms that are missing (matched by slug) from LAUNCH_ROOMS in
app/config/constants.py. Rooms that already exist are left exactly as editors
have them, so renaming a room in admin is never undone. No sample content.

    python scripts/create_launch_rooms.py           # preview
    python scripts/create_launch_rooms.py --apply   # create the missing rooms
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from pymongo.errors import DuplicateKeyError, PyMongoError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.constants import LAUNCH_ROOMS  # noqa: E402
from app.config.settings import settings  # noqa: E402
from app.database.indexes import create_indexes  # noqa: E402
from app.database.mongodb import close_mongo_connection, connect_to_mongo, get_database  # noqa: E402
from app.models.category import CATEGORY_COLLECTION, create_category_document  # noqa: E402


async def missing_rooms(db: Any) -> list[dict[str, Any]]:
    return [room for room in LAUNCH_ROOMS if not await db[CATEGORY_COLLECTION].find_one({"slug": room["slug"]}, {"_id": 1})]


async def create_missing_rooms(db: Any) -> list[str]:
    """Insert the missing launch rooms; returns the slugs it created."""
    created = []
    for room in await missing_rooms(db):
        document = create_category_document(
            name=str(room["name"]),
            slug=str(room["slug"]),
            subtitle=str(room["subtitle"]),
            description=str(room["description"]),
            nav_order=int(room["nav_order"]),
        ).to_mongo()
        try:
            await db[CATEGORY_COLLECTION].insert_one(document)
            created.append(str(room["slug"]))
        except DuplicateKeyError:
            pass  # created at the same moment elsewhere
    return created


async def main() -> int:
    parser = argparse.ArgumentParser(description="Create the six launch rooms if they are missing.")
    parser.add_argument("--apply", action="store_true", help="create them (without this, only preview)")
    args = parser.parse_args()

    print(f"Database: {settings.mongodb_db_name}")
    try:
        await connect_to_mongo()
        db = get_database()
        missing = await missing_rooms(db)
        for room in LAUNCH_ROOMS:
            state = "missing, will create" if room in missing else "exists, left as is"
            print(f"  {room['slug']:<18} {room['name']} ({state})")
        if not args.apply:
            print("\nPreview only. Rerun with --apply to create the missing rooms.")
            return 0
        await create_indexes()
        created = await create_missing_rooms(db)
    except PyMongoError as exc:
        print(f"MongoDB error: {exc}", file=sys.stderr)
        return 1
    finally:
        await close_mongo_connection()

    print(f"\nCreated {len(created)} room(s): {', '.join(created) or 'none needed'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
