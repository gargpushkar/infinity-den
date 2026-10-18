"""Delete member accounts by email address, and everything they wrote.

The same deletion as /admin/deletions. Without --apply it only shows what
would be removed. Members who had asked to be deleted get a confirmation email.

    python scripts/delete_members.py one@example.com two@example.com
    python scripts/delete_members.py --file emails.txt
    python scripts/delete_members.py --file emails.txt --apply
"""

import argparse
import asyncio
import sys
from pathlib import Path

from pymongo.errors import PyMongoError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.database.mongodb import close_mongo_connection, connect_to_mongo, get_database  # noqa: E402
from app.services.account_deletion_service import (  # noqa: E402
    MAX_BATCH,
    AccountDeletionService,
    parse_emails,
    send_deleted_emails,
)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Delete member accounts by email address.")
    parser.add_argument("emails", nargs="*", help="email addresses")
    parser.add_argument("--file", type=Path, help="a file of addresses (commas, spaces, or one per line)")
    parser.add_argument("--apply", action="store_true", help="delete (without this, only preview)")
    args = parser.parse_args()

    text = " ".join(args.emails) + (" " + args.file.read_text() if args.file else "")
    emails = parse_emails(text)
    if not emails:
        parser.error("give at least one email address")
    if len(set(text.lower().replace(",", " ").replace(";", " ").split())) > MAX_BATCH:
        print(f"Only the first {MAX_BATCH} addresses are handled per run; run again for the rest.")

    print(f"Database: {settings.mongodb_db_name}\n")
    try:
        await connect_to_mongo()
        service = AccountDeletionService(get_database())
        rows = await service.preview(emails)
        for row in rows:
            if not row["found"]:
                print(f"  {row['email']}: no account")
                continue
            asked = "asked to be deleted" if row["requested"] else "did not ask"
            print(f"  {row['email']}: {row['display_name']} (@{row['username']}), {asked}; "
                  f"{row['pieces']} pieces, {row['responses']} responses, {row['arguments']} arguments, {row['comments']} comments, {row['saved']} saved")
        found = [row["email"] for row in rows if row["found"]]
        if not args.apply:
            print(f"\nPreview only. Rerun with --apply to delete {len(found)} account(s).")
            return 0
        results = await service.delete_by_emails(found, editor="script")
        await send_deleted_emails(results)
    except PyMongoError as exc:
        print(f"MongoDB error: {exc}", file=sys.stderr)
        return 1
    finally:
        await close_mongo_connection()

    print(f"\nDeleted {sum(r['deleted'] for r in results)} account(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
