"""Seed the featured business directory.

    python -m scripts.seed_businesses            # preview
    python -m scripts.seed_businesses --apply    # write

Idempotent: businesses are upserted by slug, so rerunning is safe.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from app.database.indexes import create_indexes
from app.database.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.models.business import BUSINESS_COLLECTION, create_business_document


BUSINESSES: list[dict[str, Any]] = [
    {
        "name": "Northwind Coffee",
        "slug": "northwind-coffee",
        "tagline": "Small-batch roasters supplying cafes across the city.",
        "logo": "/static/images/articles/newsletter-loops.svg",
        "website_url": "https://example.com/northwind-coffee",
        "category_id": "food",
        "location": "Bristol, UK",
        "sort_order": 10,
    },
    {
        "name": "Meridian Bank",
        "slug": "meridian-bank",
        "tagline": "Everyday banking with no fees abroad.",
        "logo": "/static/images/articles/content-engine.svg",
        "website_url": "https://example.com/meridian-bank",
        "category_id": "business",
        "location": "London, UK",
        "sort_order": 20,
    },
    {
        "name": "Kestrel Outfitters",
        "slug": "kestrel-outfitters",
        "tagline": "Luggage and layers built for long journeys.",
        "logo": "/static/images/articles/contributors.svg",
        "website_url": "https://example.com/kestrel-outfitters",
        "category_id": "travel",
        "location": "Edinburgh, UK",
        "sort_order": 30,
    },
    {
        "name": "Lumen Labs",
        "slug": "lumen-labs",
        "tagline": "Independent hardware reviews and repair guides.",
        "logo": "/static/images/articles/search-traffic.svg",
        "website_url": "https://example.com/lumen-labs",
        "category_id": "tech",
        "location": "Manchester, UK",
        "sort_order": 40,
    },
]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the changes.")
    args = parser.parse_args()

    await connect_to_mongo()
    try:
        db = get_database()
        existing = await db[BUSINESS_COLLECTION].count_documents({})

        if not args.apply:
            print("DRY RUN - nothing has been written.\n")
            print(f"  Businesses now:  {existing}")
            print(f"  Would UPSERT:    {len(BUSINESSES)} (all featured)")
            for business in BUSINESSES:
                print(f"                     {business['slug']}")
            print("\nRerun with --apply to write these changes.")
            return

        for business in BUSINESSES:
            document = create_business_document(
                is_featured=True,
                **business,
            ).to_mongo()
            # Preserve the original created_at when the record already exists.
            document.pop("created_at", None)
            await db[BUSINESS_COLLECTION].update_one(
                {"slug": business["slug"]},
                {
                    "$set": document,
                    "$setOnInsert": {"created_at": document["updated_at"]},
                },
                upsert=True,
            )

        await create_indexes()
        total = await db[BUSINESS_COLLECTION].count_documents({})
        print(f"Upserted {len(BUSINESSES)} businesses. Directory now holds {total}.")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
