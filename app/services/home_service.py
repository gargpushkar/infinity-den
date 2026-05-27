async def get_homepage_context() -> dict[str, list[dict[str, str]] | list[str]]:
    hero_metrics = [
        {"value": "5", "label": "Editorial channels"},
        {"value": "24h", "label": "Publishing rhythm"},
        {"value": "SEO", "label": "Ready by default"},
    ]

    top_articles = [
        {
            "title": "Editorial systems that scale with your audience",
            "slug": "#",
            "excerpt": "A practical look at building a publishing rhythm, review process, and SEO workflow without slowing the team down.",
            "category": "Editorial",
            "read_time": "8 min read",
            "cover_image": "/static/images/articles/editorial-default.svg",
            "image_alt": "Abstract editorial article layout",
        },
        {
            "title": "How to turn category pages into growth assets",
            "slug": "#",
            "excerpt": "Use focused topic hubs to make discovery easier for readers and search engines.",
            "category": "SEO",
            "read_time": "6 min read",
            "cover_image": "/static/images/articles/search-traffic.svg",
            "image_alt": "Search growth dashboard illustration",
        },
        {
            "title": "A cleaner intake process for guest contributors",
            "slug": "#",
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
            "slug": "#",
            "excerpt": "Plan, publish, and optimize editorial work from one clean platform.",
            "category": "Strategy",
            "cover_image": "/static/images/articles/content-engine.svg",
            "image_alt": "Notebook and laptop arranged for editorial planning",
            "read_time": "5 min read",
        },
        {
            "title": "Turn expertise into durable search traffic",
            "slug": "#",
            "excerpt": "A publishing workflow shaped around discoverability and trust.",
            "category": "SEO",
            "cover_image": "/static/images/articles/search-traffic.svg",
            "image_alt": "Search analytics dashboard on a laptop",
            "read_time": "6 min read",
        },
        {
            "title": "Invite expert contributors",
            "slug": "#",
            "excerpt": "Collect and review article ideas without losing editorial control.",
            "category": "Community",
            "cover_image": "/static/images/articles/contributors.svg",
            "image_alt": "Editorial contributors collaborating around a table",
            "read_time": "4 min read",
        },
        {
            "title": "Create newsletter loops readers trust",
            "slug": "#",
            "excerpt": "Make subscriptions useful with clear themes, reliable cadence, and thoughtful routing.",
            "category": "Newsletter",
            "cover_image": "/static/images/articles/newsletter-loops.svg",
            "image_alt": "Newsletter performance and publishing tools on a screen",
            "read_time": "7 min read",
        },
    ]

    return {
        "hero_metrics": hero_metrics,
        "top_articles": top_articles,
        "featured_articles": featured_articles,
        "categories": ["Content Marketing", "SEO", "Editorial", "Growth", "Newsletter"],
    }
