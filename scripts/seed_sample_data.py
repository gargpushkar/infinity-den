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
        "title": "Designing a Durable Editorial Operating System",
        "slug": "designing-a-durable-editorial-operating-system",
        "excerpt": "A long-form sample article for testing article detail layouts, reading flow, metadata, and responsive content spacing.",
        "category_id": "editorial-ops",
        "tags": ["Editorial", "Playbooks", "Analytics"],
        "author": "Priya Nair",
        "cover_image": "/static/images/articles/editorial-default.svg",
        "is_featured": True,
        "status": "published",
        "published_days_ago": 1,
        "views": 2240,
        "content_variant": "long_form",
    },
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


def _long_form_article_content() -> str:
    paragraphs = (
        "Designing a Durable Editorial Operating System",
        (
            "A publishing team feels calm when every person can see what is moving, "
            "what is blocked, and what needs a decision before the next article goes "
            "live. The operating system behind that feeling is not a single tool or "
            "a heroic editor carrying the whole process in memory. It is a shared "
            "set of rituals, fields, review moments, and quality standards that make "
            "good work easier to repeat. This long sample article exists to stretch "
            "the article detail layout with realistic paragraphs, varied sentence "
            "lengths, and enough body copy to test reading rhythm on desktop, tablet, "
            "and mobile screens."
        ),
        (
            "The first layer is intake. Every idea should enter the system with the "
            "same minimum shape: audience, promise, source of demand, owner, format, "
            "and next action. That sounds basic, but it prevents a backlog from "
            "turning into a drawer of vague possibilities. A strong intake habit lets "
            "editors compare ideas quickly, merge duplicates, pause weak angles, and "
            "spot themes that deserve a larger package. It also gives writers enough "
            "context to understand why a story matters before they begin drafting."
        ),
        (
            "The second layer is prioritization. Teams often say they need more ideas "
            "when they really need a sharper way to choose among the ideas they "
            "already have. A durable editorial workflow scores work by reader value, "
            "business relevance, effort, freshness, and confidence. The score is not "
            "a substitute for judgment; it is a prompt for better judgment. When two "
            "articles compete for the same publishing window, the team can discuss "
            "evidence instead of taste alone."
        ),
        (
            "The third layer is briefing. A good brief is not a script. It is a map of "
            "the terrain: who the piece is for, what problem it solves, which claims "
            "need proof, which internal examples should appear, and what a reader "
            "should be able to do after finishing. Writers still bring voice, "
            "structure, and discovery to the work. The brief simply removes avoidable "
            "confusion, especially when contributors, subject matter experts, and "
            "editors are working across different schedules."
        ),
        (
            "The fourth layer is production visibility. A kanban board can help, but "
            "only if the states mean something precise. Idea, brief, draft, edit, "
            "fact check, design, scheduled, published, and refresh are useful stages "
            "because each one has a clear owner and exit condition. If a card sits in "
            "edit for five days, the system should reveal whether it needs a decision, "
            "a source, a headline, or a rewrite. Visibility is valuable when it tells "
            "people where to help."
        ),
        (
            "The fifth layer is quality control. Many teams rely on one final review, "
            "which makes quality feel like a bottleneck instead of a shared practice. "
            "A better system distributes checks across the process. The brief checks "
            "audience and angle. The draft review checks structure and usefulness. "
            "The copy edit checks clarity, grammar, claims, links, and formatting. "
            "The pre-publish review checks metadata, image treatment, accessibility, "
            "and internal paths. Each checkpoint is small enough to complete without "
            "drama."
        ),
        (
            "The sixth layer is measurement. Analytics become healthier when they are "
            "connected to editorial intent. A search article might be judged by "
            "rankings, qualified entrances, and internal click-through. A thought "
            "leadership essay might be judged by saves, replies, sales-team reuse, "
            "and newsletter engagement. A contributor story might be judged by "
            "relationship value and referral quality. The same dashboard cannot tell "
            "the truth about every format unless it preserves the purpose of each "
            "piece."
        ),
        (
            "The seventh layer is refresh planning. Publishing is not the finish line "
            "for evergreen work. The system should record when an article needs a "
            "freshness review, which facts age quickly, which screenshots may break, "
            "and which related pieces should be checked at the same time. Refreshing "
            "an article is usually cheaper than starting over, and it protects the "
            "trust readers place in the archive. A strong archive feels alive because "
            "someone is responsible for its accuracy."
        ),
        (
            "The eighth layer is feedback. Editors need qualitative signals, not just "
            "traffic charts. Sales questions, support tickets, newsletter replies, "
            "community discussions, and search queries can all reveal missing angles. "
            "The operating system should make those signals easy to capture and route "
            "back into the backlog. When feedback stays scattered across chat threads "
            "and meetings, the team keeps rediscovering the same lessons. When it is "
            "captured well, every article teaches the next one."
        ),
        (
            "The ninth layer is governance. Someone must know who can publish, who can "
            "approve sensitive claims, how legal review is triggered, and when an "
            "article should be archived. Governance sounds heavy until a risky piece "
            "is moving quickly. Clear rules help teams move faster because they reduce "
            "guesswork. The goal is not to add meetings. The goal is to make the right "
            "decision path obvious before urgency arrives."
        ),
        (
            "The tenth layer is interface design. A publishing platform should show "
            "the right amount of information at the right moment. Writers need briefs, "
            "examples, deadlines, and comments. Editors need state, owner, risk, "
            "quality checks, and history. Leaders need throughput, focus areas, and "
            "outcomes. Readers need clean pages, useful metadata, related paths, and "
            "fast rendering. When the interface respects each role, the system feels "
            "lighter even though it is doing more work."
        ),
        (
            "This is why long-form sample content matters during development. Short "
            "placeholder copy can hide layout problems: sticky sidebars never travel, "
            "paragraph spacing never accumulates, related sections sit too high, and "
            "mobile reading never feels like a real session. A twelve-hundred-word "
            "sample exposes those issues early. It lets the team judge line length, "
            "image scale, metadata density, scrolling comfort, and the transition from "
            "body copy to the next recommended article."
        ),
        (
            "The eleventh layer is documentation. A team should be able to explain how "
            "an article moves from idea to archive without calling a meeting. The "
            "documentation does not need to be long, but it should answer the everyday "
            "questions: where ideas live, how priorities are set, what each status "
            "means, who approves sensitive edits, how images are chosen, and what "
            "must be checked before publish. When the process is written down, new "
            "teammates ramp faster and experienced teammates spend less energy "
            "remembering invisible rules."
        ),
        (
            "The twelfth layer is cadence. Even a thoughtful system loses value if it "
            "is reviewed only when something breaks. A monthly editorial operations "
            "review can surface bottlenecks, stale drafts, missing categories, and "
            "articles that deserve a refresh. The meeting should be practical: look "
            "at flow, choose fixes, assign owners, and close the loop next time. "
            "Cadence turns process improvement into a habit rather than a rescue "
            "mission, which is how teams stay steady as the archive and audience grow."
        ),
        (
            "A durable editorial operating system does not remove creative work from "
            "publishing. It protects creative work from avoidable friction. The best "
            "systems make room for judgment while keeping the basics reliable: clear "
            "ideas, useful briefs, visible ownership, careful review, honest metrics, "
            "and a maintained archive. When those pieces hold together, a team can "
            "publish more consistently without becoming mechanical, and readers can "
            "trust that each article belongs to a larger body of thoughtful work. "
            "That trust is the real output of the system: not simply more posts, but "
            "a clearer promise that the next useful answer will be easy to find. "
            "It also gives designers enough scroll depth to evaluate the reading page honestly."
        ),
    )

    return "\n\n".join(paragraphs)


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
            content=(
                _long_form_article_content()
                if sample.get("content_variant") == "long_form"
                else _article_content(sample["title"], sample["category_id"])
            ),
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
