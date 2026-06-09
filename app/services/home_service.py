async def get_homepage_context() -> dict[str, list[dict[str, str]] | list[str]]:
    category_links = [
        {
            "name": "Content Strategy",
            "url": "/articles?category=content-strategy",
        },
        {
            "name": "Search Growth",
            "url": "/articles?category=search-growth",
        },
        {
            "name": "Editorial Ops",
            "url": "/articles?category=editorial-ops",
        },
        {
            "name": "Audience Building",
            "url": "/articles?category=audience-building",
        },
        {
            "name": "Newsletter",
            "url": "/search?q=newsletter",
        },
    ]
    hero_metrics = [
        {"value": "5", "label": "Editorial channels"},
        {"value": "24h", "label": "Publishing rhythm"},
        {"value": "SEO", "label": "Ready by default"},
    ]

    top_articles = [
        {
            "title": "Editorial systems that scale with your audience",
            "url": "/articles?category=editorial-ops",
            "excerpt": "A practical look at building a publishing rhythm, review process, and SEO workflow without slowing the team down.",
            "category": "Editorial",
            "read_time": "8 min read",
            "cover_image": "/static/images/articles/editorial-default.svg",
            "image_alt": "Abstract editorial article layout",
        },
        {
            "title": "How to turn category pages into growth assets",
            "url": "/categories",
            "excerpt": "Use focused topic hubs to make discovery easier for readers and search engines.",
            "category": "SEO",
            "read_time": "6 min read",
            "cover_image": "/static/images/articles/search-traffic.svg",
            "image_alt": "Search growth dashboard illustration",
        },
        {
            "title": "A cleaner intake process for guest contributors",
            "url": "/#writeForUs",
            "excerpt": "Collect ideas, triage submissions, and protect the quality bar from the first message.",
            "category": "Community",
            "read_time": "5 min read",
            "cover_image": "/static/images/articles/contributors.svg",
            "image_alt": "Contributor collaboration illustration",
        },
    ]

    featured_articles = [
        {
            "title": "Build a sharper content engine",
            "url": "/articles?category=content-strategy",
            "excerpt": "Plan, publish, and optimize editorial work from one clean platform.",
            "category": "Strategy",
            "cover_image": "/static/images/articles/content-engine.svg",
            "image_alt": "Notebook and laptop arranged for editorial planning",
            "read_time": "5 min read",
        },
        {
            "title": "Turn expertise into durable search traffic",
            "url": "/articles?category=search-growth",
            "excerpt": "A publishing workflow shaped around discoverability and trust.",
            "category": "SEO",
            "cover_image": "/static/images/articles/search-traffic.svg",
            "image_alt": "Search analytics dashboard on a laptop",
            "read_time": "6 min read",
        },
        {
            "title": "Invite expert contributors",
            "url": "/#writeForUs",
            "excerpt": "Collect and review article ideas without losing editorial control.",
            "category": "Community",
            "cover_image": "/static/images/articles/contributors.svg",
            "image_alt": "Editorial contributors collaborating around a table",
            "read_time": "4 min read",
        },
        {
            "title": "Create newsletter loops readers trust",
            "url": "/#newsletterSignup",
            "excerpt": "Make subscriptions useful with clear themes, reliable cadence, and thoughtful routing.",
            "category": "Newsletter",
            "cover_image": "/static/images/articles/newsletter-loops.svg",
            "image_alt": "Newsletter performance and publishing tools on a screen",
            "read_time": "7 min read",
        },
    ]

    latest_articles = [
        {
            "title": "A weekly editorial review that keeps teams aligned",
            "url": "/articles?category=editorial-ops",
            "excerpt": "Use a short review ritual to spot stale drafts, unblock approvals, and keep the publishing calendar honest.",
            "category": "Editorial",
            "cover_image": "/static/images/articles/editorial-default.svg",
            "image_alt": "Editorial planning board with article cards",
            "read_time": "7 min read",
        },
        {
            "title": "What to measure before refreshing old content",
            "url": "/search?q=content+refresh",
            "excerpt": "Prioritize updates with search intent, decay signals, and conversion context instead of chasing every aging post.",
            "category": "Growth",
            "cover_image": "/static/images/articles/search-traffic.svg",
            "image_alt": "Search analytics charts for content refresh decisions",
            "read_time": "6 min read",
        },
        {
            "title": "Turn contributor pitches into a reliable intake queue",
            "url": "/#writeForUs",
            "excerpt": "Separate promising ideas from noisy submissions with clear prompts, topic lanes, and review states.",
            "category": "Community",
            "cover_image": "/static/images/articles/contributors.svg",
            "image_alt": "Contributors reviewing article ideas together",
            "read_time": "5 min read",
        },
        {
            "title": "Newsletter sections that make repeat reading easier",
            "url": "/#newsletterSignup",
            "excerpt": "Design recurring newsletter blocks that help subscribers recognize value before they reach the first link.",
            "category": "Newsletter",
            "cover_image": "/static/images/articles/newsletter-loops.svg",
            "image_alt": "Newsletter layout and engagement workflow",
            "read_time": "4 min read",
        },
        {
            "title": "How category pages can guide editorial planning",
            "url": "/categories",
            "excerpt": "Use category hubs as living maps for coverage gaps, internal links, and reader journeys.",
            "category": "SEO",
            "cover_image": "/static/images/articles/content-engine.svg",
            "image_alt": "Content strategy workspace with publishing tools",
            "read_time": "8 min read",
        },
    ]

    return {
        "hero_metrics": hero_metrics,
        "top_articles": top_articles,
        "featured_articles": featured_articles,
        "latest_articles": latest_articles,
        "categories": [category["name"] for category in category_links],
        "category_links": category_links,
    }
