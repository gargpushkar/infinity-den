"""Reseed the publication around Business / Tech / Food / Travel.

The original sample data described a content-marketing niche site and does not
fit the new navigation. This script removes that specific seed content by slug
and installs topics and articles that exercise every homepage rail.

It is destructive but narrow: it only deletes the documents listed in
LEGACY_CATEGORY_SLUGS and LEGACY_ARTICLE_SLUGS. Anything you wrote yourself is
left alone, and rerunning the script is safe.

    python -m scripts.seed_infinity_den            # preview, changes nothing
    python -m scripts.seed_infinity_den --apply    # actually write
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from app.database.indexes import create_indexes
from app.database.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.models.article import ARTICLE_COLLECTION, create_article_document
from app.models.category import CATEGORY_COLLECTION


NOW = datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc)

# Seed content from the previous publication, removed by exact slug.
LEGACY_CATEGORY_SLUGS: tuple[str, ...] = (
    "content-strategy",
    "search-growth",
    "editorial-ops",
    "audience-building",
)
LEGACY_ARTICLE_SLUGS: tuple[str, ...] = (
    "designing-a-durable-editorial-operating-system",
    "build-a-content-engine-that-compounds",
    "how-to-map-search-intent-before-writing",
    "the-editors-weekly-review-checklist",
    "newsletter-loops-that-bring-readers-back",
    "a-better-brief-for-contributor-articles",
    "measure-content-quality-without-vanity-metrics",
    "technical-seo-checks-for-new-articles",
)

# Articles that predate the new taxonomy and should be adopted rather than
# deleted. Maps article slug -> category slug.
ADOPT_ARTICLES: dict[str, str] = {
    "hello-world-by-pushkar": "tech",
}

CATEGORIES: list[dict[str, Any]] = [
    {
        "name": "Business",
        "slug": "business",
        "description": "Startups, money, markets, and the people building them.",
        "image": "/static/images/articles/content-engine.svg",
        "nav_order": 10,
    },
    {
        "name": "Tech",
        "slug": "tech",
        "description": "Hardware, software, and the tools changing how we work.",
        "image": "/static/images/articles/search-traffic.svg",
        "nav_order": 20,
    },
    {
        "name": "Food",
        "slug": "food",
        "description": "Recipes, restaurants, and the craft behind good cooking.",
        "image": "/static/images/articles/newsletter-loops.svg",
        "nav_order": 30,
    },
    {
        "name": "Travel",
        "slug": "travel",
        "description": "Destinations, itineraries, and how to move through them well.",
        "image": "/static/images/articles/contributors.svg",
        "nav_order": 40,
    },
]

TAGS: list[dict[str, str]] = [
    {"name": "Startups", "slug": "startups"},
    {"name": "Money", "slug": "money"},
    {"name": "AI", "slug": "ai"},
    {"name": "Gadgets", "slug": "gadgets"},
    {"name": "Recipes", "slug": "recipes"},
    {"name": "Restaurants", "slug": "restaurants"},
    {"name": "Destinations", "slug": "destinations"},
    {"name": "Budget", "slug": "budget"},
]

DEFAULT_IMAGE = "/static/images/articles/editorial-default.svg"


def _body(intro: str) -> str:
    return (
        f"{intro}\n\n"
        "This is sample copy used to exercise article layouts, reading time, "
        "metadata, and responsive spacing while the publication is being "
        "built out.\n\n"
        "Replace it with real editorial content before launch. The structure "
        "here is deliberately plain so that spacing and typography problems "
        "are easy to spot.\n\n"
        "A final paragraph gives the reading-time estimate something "
        "reasonable to measure against."
    )


# days_ago, views, format, editors_pick
ARTICLES: list[dict[str, Any]] = [
    # --- Business -----------------------------------------------------------
    {
        "title": "The quiet rise of the four-day working week",
        "slug": "the-quiet-rise-of-the-four-day-working-week",
        "excerpt": "Companies that cut a day are reporting steadier output and far lower attrition.",
        "category_id": "business",
        "tags": ["Startups"],
        "author": "Priya Nair",
        "article_format": "news",
        "days_ago": 1,
        "views": 4120,
        "is_featured": True,
        "is_editors_pick": True,
    },
    {
        "title": "How to read a startup balance sheet",
        "slug": "how-to-read-a-startup-balance-sheet",
        "excerpt": "A line-by-line walkthrough for founders who never trained as accountants.",
        "category_id": "business",
        "tags": ["Money", "Startups"],
        "author": "Daniel Osei",
        "article_format": "guide",
        "days_ago": 6,
        "views": 2870,
    },
    {
        "title": "Reviewed: five expense tools for small teams",
        "slug": "reviewed-five-expense-tools-for-small-teams",
        "excerpt": "We ran a quarter of real invoices through each one to see which held up.",
        "category_id": "business",
        "tags": ["Money"],
        "author": "Daniel Osei",
        "article_format": "review",
        "days_ago": 12,
        "views": 1640,
    },
    # --- Tech ---------------------------------------------------------------
    {
        "title": "What on-device AI actually changes for your phone",
        "slug": "what-on-device-ai-actually-changes-for-your-phone",
        "excerpt": "Less round-tripping to the cloud, better privacy, and a battery cost worth knowing about.",
        "category_id": "tech",
        "tags": ["AI", "Gadgets"],
        "author": "Meera Shah",
        "article_format": "news",
        "days_ago": 2,
        "views": 5210,
        "is_featured": True,
        "is_editors_pick": True,
    },
    {
        "title": "Setting up a home server without losing a weekend",
        "slug": "setting-up-a-home-server-without-losing-a-weekend",
        "excerpt": "A practical build, from picking the box to backups that actually restore.",
        "category_id": "tech",
        "tags": ["Gadgets"],
        "author": "Meera Shah",
        "article_format": "guide",
        "days_ago": 8,
        "views": 3320,
    },
    {
        "title": "Reviewed: the mechanical keyboards worth the desk space",
        "slug": "reviewed-the-mechanical-keyboards-worth-the-desk-space",
        "excerpt": "Six boards, three months of daily typing, and one clear winner.",
        "category_id": "tech",
        "tags": ["Gadgets"],
        "author": "Tom Reeves",
        "article_format": "review",
        "days_ago": 15,
        "views": 2450,
    },
    # --- Food ---------------------------------------------------------------
    {
        "title": "The case for cooking with less equipment",
        "slug": "the-case-for-cooking-with-less-equipment",
        "excerpt": "One pan, one knife, and why constraint tends to make better dinners.",
        "category_id": "food",
        "tags": ["Recipes"],
        "author": "Ana Duarte",
        "article_format": "news",
        "days_ago": 3,
        "views": 3890,
        "is_featured": True,
    },
    {
        "title": "How to build a stock that improves everything you cook",
        "slug": "how-to-build-a-stock-that-improves-everything-you-cook",
        "excerpt": "Bones, time, and restraint — the technique behind most good restaurant food.",
        "category_id": "food",
        "tags": ["Recipes"],
        "author": "Ana Duarte",
        "article_format": "guide",
        "days_ago": 9,
        "views": 2980,
        "is_editors_pick": True,
    },
    {
        "title": "Reviewed: the neighbourhood bakeries worth the queue",
        "slug": "reviewed-the-neighbourhood-bakeries-worth-the-queue",
        "excerpt": "We ate our way through fourteen of them so you can skip eleven.",
        "category_id": "food",
        "tags": ["Restaurants"],
        "author": "Ravi Menon",
        "article_format": "review",
        "days_ago": 18,
        "views": 1980,
    },
    # --- Travel -------------------------------------------------------------
    {
        "title": "Night trains are back, and they are better than you remember",
        "slug": "night-trains-are-back-and-they-are-better-than-you-remember",
        "excerpt": "New routes across Europe are making the sleeper a serious alternative to flying.",
        "category_id": "travel",
        "tags": ["Destinations"],
        "author": "Sofia Lindqvist",
        "article_format": "news",
        "days_ago": 4,
        "views": 4480,
        "is_featured": True,
        "is_editors_pick": True,
    },
    {
        "title": "How to plan a two-week trip on a one-week budget",
        "slug": "how-to-plan-a-two-week-trip-on-a-one-week-budget",
        "excerpt": "Shoulder seasons, slower transport, and the bookings worth making early.",
        "category_id": "travel",
        "tags": ["Budget", "Destinations"],
        "author": "Sofia Lindqvist",
        "article_format": "guide",
        "days_ago": 11,
        "views": 3610,
    },
    {
        "title": "Reviewed: carry-on bags that survived a year of flights",
        "slug": "reviewed-carry-on-bags-that-survived-a-year-of-flights",
        "excerpt": "Wheels, zips, and warranties tested well past the point of politeness.",
        "category_id": "travel",
        "tags": ["Budget"],
        "author": "Tom Reeves",
        "article_format": "review",
        "days_ago": 20,
        "views": 2210,
    },
]


async def _preview(db: Any) -> None:
    legacy_categories = await db[CATEGORY_COLLECTION].count_documents(
        {"slug": {"$in": list(LEGACY_CATEGORY_SLUGS)}}
    )
    legacy_articles = await db[ARTICLE_COLLECTION].count_documents(
        {"slug": {"$in": list(LEGACY_ARTICLE_SLUGS)}}
    )
    total_categories = await db[CATEGORY_COLLECTION].count_documents({})
    total_articles = await db[ARTICLE_COLLECTION].count_documents({})

    print("DRY RUN - nothing has been written.\n")
    print(f"  Database now:        {total_categories} categories, {total_articles} articles")
    print(f"  Would DELETE:        {legacy_categories} categories, {legacy_articles} articles")
    print(f"  Would UPSERT:        {len(CATEGORIES)} categories, {len(TAGS)} tags, {len(ARTICLES)} articles")
    print(f"  Would REASSIGN:      {len(ADOPT_ARTICLES)} existing article(s)")
    for slug, category in ADOPT_ARTICLES.items():
        exists = await db[ARTICLE_COLLECTION].count_documents({"slug": slug})
        state = "found" if exists else "NOT FOUND - will be skipped"
        print(f"                         {slug} -> {category} ({state})")
    print("\n  Untouched: every document whose slug is not listed above.")
    print("\nRerun with --apply to write these changes.")


async def _apply(db: Any) -> None:
    deleted_articles = await db[ARTICLE_COLLECTION].delete_many(
        {"slug": {"$in": list(LEGACY_ARTICLE_SLUGS)}}
    )
    deleted_categories = await db[CATEGORY_COLLECTION].delete_many(
        {"slug": {"$in": list(LEGACY_CATEGORY_SLUGS)}}
    )
    print(
        f"Deleted {deleted_articles.deleted_count} legacy articles and "
        f"{deleted_categories.deleted_count} legacy categories."
    )

    for category in CATEGORIES:
        await db[CATEGORY_COLLECTION].update_one(
            {"slug": category["slug"]},
            {"$set": category},
            upsert=True,
        )
    print(f"Upserted {len(CATEGORIES)} categories.")

    for tag in TAGS:
        await db.tags.update_one({"slug": tag["slug"]}, {"$set": tag}, upsert=True)
    print(f"Upserted {len(TAGS)} tags.")

    for article in ARTICLES:
        published_at = NOW - timedelta(days=article["days_ago"])
        document = create_article_document(
            title=article["title"],
            slug=article["slug"],
            excerpt=article["excerpt"],
            content=_body(article["excerpt"]),
            author=article["author"],
            cover_image=article.get("cover_image", DEFAULT_IMAGE),
            category_id=article["category_id"],
            tags=article.get("tags", []),
            is_featured=article.get("is_featured", False),
            article_format=article.get("article_format", "news"),
            is_editors_pick=article.get("is_editors_pick", False),
            status="published",
            published_at=published_at,
            views=article.get("views", 0),
        ).to_mongo()
        document["created_at"] = published_at
        document["updated_at"] = published_at

        await db[ARTICLE_COLLECTION].update_one(
            {"slug": article["slug"]},
            {"$set": document},
            upsert=True,
        )
    print(f"Upserted {len(ARTICLES)} articles.")

    # Existing articles predate the new fields; give them defaults so the
    # homepage rail filters treat them consistently.
    backfill = await db[ARTICLE_COLLECTION].update_many(
        {"article_format": {"$exists": False}},
        {
            "$set": {
                "article_format": "news",
                "is_editors_pick": False,
            }
        },
    )
    print(f"Backfilled {backfill.modified_count} pre-existing articles with defaults.")

    for article_slug, category_slug in ADOPT_ARTICLES.items():
        result = await db[ARTICLE_COLLECTION].update_one(
            {"slug": article_slug},
            {"$set": {"category_id": category_slug}},
        )
        state = "reassigned" if result.matched_count else "not found, skipped"
        print(f"  {article_slug} -> {category_slug}: {state}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the changes. Without this flag the script only reports.",
    )
    args = parser.parse_args()

    await connect_to_mongo()
    try:
        db = get_database()
        if not args.apply:
            await _preview(db)
            return

        await _apply(db)
        await create_indexes()
        print("\nIndexes ensured. Reseed complete.")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
