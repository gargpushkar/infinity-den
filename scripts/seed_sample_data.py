from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from app.database.indexes import create_indexes
from app.database.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.models.article import ARTICLE_COLLECTION, create_article_document


NOW = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)

SAMPLE_CATEGORIES: list[dict[str, str]] = [
    {
        "name": "Content Strategy",
        "slug": "content-strategy",
        "description": "Planning frameworks, editorial calendars, and audience research.",
        "image": "/static/images/articles/content-engine.svg",
    },
    {
        "name": "Search Growth",
        "slug": "search-growth",
        "description": "Practical SEO, search intent, and discoverability playbooks.",
        "image": "/static/images/articles/search-traffic.svg",
    },
    {
        "name": "Editorial Ops",
        "slug": "editorial-ops",
        "description": "Workflow, reviews, publishing systems, and team rituals.",
        "image": "/static/images/articles/editorial-default.svg",
    },
    {
        "name": "Audience Building",
        "slug": "audience-building",
        "description": "Newsletter, community, and contributor-led growth.",
        "image": "/static/images/articles/newsletter-loops.svg",
    },
]

SAMPLE_TAGS: list[dict[str, str]] = [
    {"name": "SEO", "slug": "seo"},
    {"name": "Editorial", "slug": "editorial"},
    {"name": "Newsletter", "slug": "newsletter"},
    {"name": "Analytics", "slug": "analytics"},
    {"name": "Playbooks", "slug": "playbooks"},
    {"name": "Contributors", "slug": "contributors"},
]

SAMPLE_ARTICLES: list[dict[str, Any]] = [
    {
        "title": "Build a Content Engine That Compounds",
        "slug": "build-a-content-engine-that-compounds",
        "excerpt": "A practical framework for turning scattered article ideas into a durable publishing system.",
        "category_id": "content-strategy",
        "tags": ["Playbooks", "Editorial"],
        "author": "Maya Chen",
        "cover_image": "/static/images/articles/content-engine.svg",
        "is_featured": True,
        "status": "published",
        "published_days_ago": 2,
        "views": 1840,
    },
    {
        "title": "How to Map Search Intent Before Writing",
        "slug": "how-to-map-search-intent-before-writing",
        "excerpt": "Use intent clusters to choose article angles that satisfy readers and search engines.",
        "category_id": "search-growth",
        "tags": ["SEO", "Playbooks"],
        "author": "Daniel Reyes",
        "cover_image": "/static/images/articles/search-traffic.svg",
        "is_featured": True,
        "status": "published",
        "published_days_ago": 5,
        "views": 1325,
    },
    {
        "title": "The Editor's Weekly Review Checklist",
        "slug": "the-editors-weekly-review-checklist",
        "excerpt": "A repeatable checklist for keeping article quality high without slowing the team down.",
        "category_id": "editorial-ops",
        "tags": ["Editorial", "Analytics"],
        "author": "Priya Nair",
        "cover_image": "/static/images/articles/editorial-default.svg",
        "is_featured": False,
        "status": "published",
        "published_days_ago": 8,
        "views": 896,
    },
    {
        "title": "Newsletter Loops That Bring Readers Back",
        "slug": "newsletter-loops-that-bring-readers-back",
        "excerpt": "Design newsletter sections that turn one-time visitors into returning readers.",
        "category_id": "audience-building",
        "tags": ["Newsletter", "Analytics"],
        "author": "Elena Brooks",
        "cover_image": "/static/images/articles/newsletter-loops.svg",
        "is_featured": True,
        "status": "published",
        "published_days_ago": 11,
        "views": 1112,
    },
    {
        "title": "A Better Brief for Contributor Articles",
        "slug": "a-better-brief-for-contributor-articles",
        "excerpt": "Give guest writers enough structure to succeed while preserving their voice.",
        "category_id": "audience-building",
        "tags": ["Contributors", "Editorial"],
        "author": "Jon Bell",
        "cover_image": "/static/images/articles/contributors.svg",
        "is_featured": False,
        "status": "published",
        "published_days_ago": 15,
        "views": 742,
    },
    {
        "title": "Measure Content Quality Without Vanity Metrics",
        "slug": "measure-content-quality-without-vanity-metrics",
        "excerpt": "A compact scorecard for evaluating whether articles are useful, discoverable, and memorable.",
        "category_id": "content-strategy",
        "tags": ["Analytics", "Playbooks"],
        "author": "Maya Chen",
        "cover_image": "/static/images/articles/content-engine.svg",
        "is_featured": False,
        "status": "published",
        "published_days_ago": 18,
        "views": 679,
    },
    {
        "title": "Technical SEO Checks for New Articles",
        "slug": "technical-seo-checks-for-new-articles",
        "excerpt": "A short pre-publish routine for slugs, metadata, headings, and internal links.",
        "category_id": "search-growth",
        "tags": ["SEO", "Editorial"],
        "author": "Daniel Reyes",
        "cover_image": "/static/images/articles/search-traffic.svg",
        "is_featured": False,
        "status": "published",
        "published_days_ago": 21,
        "views": 958,
    },
    {
        "title": "From Draft Queue to Publishing Rhythm",
        "slug": "from-draft-queue-to-publishing-rhythm",
        "excerpt": "How to turn a backlog of half-finished ideas into a reliable editorial cadence.",
        "category_id": "editorial-ops",
        "tags": ["Editorial", "Playbooks"],
        "author": "Priya Nair",
        "cover_image": "/static/images/articles/editorial-default.svg",
        "is_featured": False,
        "status": "draft",
        "published_days_ago": None,
        "views": 0,
    },
    {
        "title": "The Homepage Content Mix We Are Testing",
        "slug": "the-homepage-content-mix-we-are-testing",
        "excerpt": "An internal draft for balancing featured stories, category modules, and conversion CTAs.",
        "category_id": "content-strategy",
        "tags": ["Analytics", "Newsletter"],
        "author": "Elena Brooks",
        "cover_image": "/static/images/articles/editorial-default.svg",
        "is_featured": False,
        "status": "draft",
        "published_days_ago": None,
        "views": 0,
    },
    {
        "title": "Retired Keyword Lists and What Replaced Them",
        "slug": "retired-keyword-lists-and-what-replaced-them",
        "excerpt": "A historical note on why our search workflow moved from keyword dumps to intent maps.",
        "category_id": "search-growth",
        "tags": ["SEO", "Analytics"],
        "author": "Daniel Reyes",
        "cover_image": "/static/images/articles/search-traffic.svg",
        "is_featured": False,
        "status": "archived",
        "published_days_ago": 90,
        "views": 302,
    },
]


def _article_content(title: str, category_id: str) -> str:
    return (
        f"{title}\n\n"
        "This sample article gives the interface enough realistic copy to exercise "
        "cards, excerpts, detail pages, metadata, filters, and pagination. It is "
        f"part of the {category_id.replace('-', ' ')} sample collection.\n\n"
        "Use it while developing layouts, then replace it with real editorial "
        "content when the publishing workflow is ready."
    )


async def seed_categories() -> int:
    db = get_database()
    changed = 0

    for category in SAMPLE_CATEGORIES:
        result = await db.categories.update_one(
            {"slug": category["slug"]},
            {"$set": category},
            upsert=True,
        )
        changed += result.modified_count + int(result.upserted_id is not None)

    return changed


async def seed_tags() -> int:
    db = get_database()
    changed = 0

    for tag in SAMPLE_TAGS:
        result = await db.tags.update_one(
            {"slug": tag["slug"]},
            {"$set": tag},
            upsert=True,
        )
        changed += result.modified_count + int(result.upserted_id is not None)

    return changed


async def seed_articles() -> int:
    db = get_database()
    articles = db[ARTICLE_COLLECTION]
    changed = 0

    for index, sample in enumerate(SAMPLE_ARTICLES):
        published_days_ago = sample["published_days_ago"]
        published_at = (
            NOW - timedelta(days=published_days_ago)
            if published_days_ago is not None
            else None
        )
        article = create_article_document(
            title=sample["title"],
            slug=sample["slug"],
            excerpt=sample["excerpt"],
            content=_article_content(sample["title"], sample["category_id"]),
            cover_image=sample["cover_image"],
            author=sample["author"],
            category_id=sample["category_id"],
            tags=sample["tags"],
            is_featured=sample["is_featured"],
            status=sample["status"],
            seo_title=sample["title"],
            seo_description=sample["excerpt"],
            published_at=published_at,
        ).to_mongo()
        article["views"] = sample["views"]
        article["created_at"] = NOW - timedelta(days=published_days_ago or index + 1)
        article["updated_at"] = NOW - timedelta(hours=index)

        result = await articles.update_one(
            {"slug": article["slug"]},
            {"$set": article},
            upsert=True,
        )
        changed += result.modified_count + int(result.upserted_id is not None)

    return changed


async def main() -> None:
    await connect_to_mongo()
    try:
        await create_indexes()
        category_count = await seed_categories()
        tag_count = await seed_tags()
        article_count = await seed_articles()
    finally:
        await close_mongo_connection()

    print(
        "Seeded sample data: "
        f"{len(SAMPLE_CATEGORIES)} categories ({category_count} changed), "
        f"{len(SAMPLE_TAGS)} tags ({tag_count} changed), "
        f"{len(SAMPLE_ARTICLES)} articles ({article_count} changed)."
    )


if __name__ == "__main__":
    asyncio.run(main())
