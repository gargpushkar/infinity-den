ARTICLE_STATUS_DRAFT = "draft"
ARTICLE_STATUS_PUBLISHED = "published"
ARTICLE_STATUS_ARCHIVED = "archived"

SUBMISSION_STATUS_NEW = "new"
SUBMISSION_STATUS_REVIEWING = "reviewing"
SUBMISSION_STATUS_ACCEPTED = "accepted"
SUBMISSION_STATUS_REJECTED = "rejected"

ARTICLE_FORMAT_ARTICLE = "article"
ARTICLE_FORMAT_EXPERIENCE = "experience"
ARTICLE_FORMAT_PERSPECTIVE = "perspective"

# The label readers see, so they always know what kind of claim they are
# reading. See vision.md -> CONTRIBUTION FORMATS.
ARTICLE_FORMAT_LABELS: dict[str, str] = {
    ARTICLE_FORMAT_ARTICLE: "Researched",
    ARTICLE_FORMAT_EXPERIENCE: "Personal experience",
    ARTICLE_FORMAT_PERSPECTIVE: "Opinion",
}
SPECULATIVE_LABEL = "Speculation"

# Launch rooms from vision.md. Slugs are permanent; names and subtitles are
# display text and can change. The seed script and the no-database fallback
# both read from here.
LAUNCH_ROOMS: tuple[dict[str, str | int], ...] = (
    {
        "slug": "science",
        "name": "Cosmic Canvas",
        "subtitle": "Science, Space & the Universe",
        "description": "The mysteries of space, scientific discoveries, nature, physics, and the laws that shape our world.",
        "nav_order": 10,
    },
    {
        "slug": "psychology",
        "name": "The Innerverse",
        "subtitle": "Psychology, Emotions & Human Behavior",
        "description": "The mind, human nature, habits, relationships, feelings, and the reasons behind our choices.",
        "nav_order": 20,
    },
    {
        "slug": "history",
        "name": "Echoes of Time",
        "subtitle": "History, Civilizations & Biographies",
        "description": "Forgotten stories, lost civilizations, influential people, and events that shaped our present.",
        "nav_order": 30,
    },
    {
        "slug": "technology",
        "name": "Beyond the Binary",
        "subtitle": "Technology, AI & the Future",
        "description": "Emerging technologies, artificial intelligence, digital culture, inventions, and tomorrow's possibilities.",
        "nav_order": 40,
    },
    {
        "slug": "philosophy",
        "name": "The Unanswered",
        "subtitle": "Philosophy, Ethics & Big Questions",
        "description": "Questions about existence, truth, morality, consciousness, freedom, and the meaning of life.",
        "nav_order": 50,
    },
    {
        "slug": "personal-stories",
        "name": "Unfiltered Lives",
        "subtitle": "Personal Stories, Experiences & Life Lessons",
        "description": "Real experiences, turning points, mistakes, growth, and the lessons people discover through living.",
        "nav_order": 60,
    },
)
