"""Contributor reputation: strengths a member has earned, shown on their profile.

There is no score and no ranking. A strength is earned or not, and each one
says why in plain words. They come from what readers rate (clarity, evidence,
reasoning) and what editors pick, never from popularity:

- a rated strength needs RATED_ARGUMENTS_NEEDED arguments in closed debates,
  each with at least RATINGS_NEEDED ratings, averaging MIN_AVERAGE or higher
  on that dimension (closed debates only, so profiles never reveal averages
  the debate page still keeps blind);
- "Well-sourced" can also come from WELL_SOURCED_PIECES researched pieces,
  whose sources editors checked before publishing;
- "Editor's pick" and "Thoughtful rebuttals" need one featured item.

Generated text never uses pronouns: the site doesn't know anyone's.
"""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.constants import ARTICLE_FORMAT_ARTICLE, ARTICLE_STATUS_PUBLISHED, RATINGS_NEEDED
from app.models.article import ARTICLE_COLLECTION
from app.models.debate import ARGUMENT_COLLECTION, REBUTTAL_COLLECTION
from app.models.question import RESPONSE_COLLECTION


RATED_ARGUMENTS_NEEDED = 3
MIN_AVERAGE = 4.0
WELL_SOURCED_PIECES = 3

# (key, label, the rating dimension it reads)
RATED_STRENGTHS: tuple[tuple[str, str, str], ...] = (
    ("well_sourced", "Well-sourced", "evidence"),
    ("clear_explainer", "Clear explainer", "clarity"),
    ("sound_reasoning", "Sound reasoning", "reasoning"),
)

# What the owner's guide says about each strength.
STRENGTH_GUIDE: tuple[tuple[str, str], ...] = (
    ("Well-sourced", f"{RATED_ARGUMENTS_NEEDED} or more debate arguments averaging {MIN_AVERAGE:.1f} or higher for evidence, or {WELL_SOURCED_PIECES} published researched pieces"),
    ("Clear explainer", f"{RATED_ARGUMENTS_NEEDED} or more debate arguments averaging {MIN_AVERAGE:.1f} or higher for clarity"),
    ("Sound reasoning", f"{RATED_ARGUMENTS_NEEDED} or more debate arguments averaging {MIN_AVERAGE:.1f} or higher for reasoning"),
    ("Editor's pick", "An editor features one of your pieces, responses, or arguments"),
    ("Thoughtful rebuttals", "An editor marks one of your rebuttals thoughtful"),
)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def earned_strengths(
    *, rated_arguments: list[dict[str, Any]], researched_pieces: int, featured: int, thoughtful_rebuttals: int
) -> list[dict[str, str]]:
    """The strengths earned, in a fixed order, each with its reason.

    `rated_arguments` holds the averages of the member's arguments in closed
    debates ({"count", "clarity", "evidence", "reasoning"}).
    """
    counted = [a for a in rated_arguments if a["count"] >= RATINGS_NEEDED]
    strengths = []
    for key, label, dimension in RATED_STRENGTHS:
        average = round(sum(a[dimension] for a in counted) / len(counted), 1) if counted else 0
        rated = len(counted) >= RATED_ARGUMENTS_NEEDED and average >= MIN_AVERAGE
        reasons = [f"{dimension.capitalize()} rated {average:.1f} across {_plural(len(counted), 'argument')}"] if rated else []
        if key == "well_sourced" and researched_pieces >= WELL_SOURCED_PIECES:
            reasons.append(f"{_plural(researched_pieces, 'researched piece')} published")
        if reasons:
            strengths.append({"key": key, "label": label, "detail": ", and ".join(reasons)})
    if featured:
        strengths.append({"key": "editors_pick", "label": "Editor's pick", "detail": f"{_plural(featured, 'contribution')} featured by editors"})
    if thoughtful_rebuttals:
        strengths.append({
            "key": "thoughtful_rebuttals", "label": "Thoughtful rebuttals",
            "detail": f"{_plural(thoughtful_rebuttals, 'rebuttal')} marked thoughtful by editors",
        })
    return strengths


async def featured_and_researched(db: AsyncIOMotorDatabase, member_id: str) -> tuple[int, int, int]:
    """(featured contributions, published researched pieces, thoughtful rebuttals)."""
    published = {"author_id": member_id, "status": ARTICLE_STATUS_PUBLISHED}
    featured = (
        await db[ARTICLE_COLLECTION].count_documents({**published, "$or": [{"is_featured": True}, {"is_editors_pick": True}]})
        + await db[RESPONSE_COLLECTION].count_documents({"user_id": member_id, "status": "published", "is_featured": True})
        + await db[ARGUMENT_COLLECTION].count_documents({"user_id": member_id, "status": "published", "is_featured": True})
    )
    researched = await db[ARTICLE_COLLECTION].count_documents({**published, "article_format": ARTICLE_FORMAT_ARTICLE})
    thoughtful = await db[REBUTTAL_COLLECTION].count_documents({"user_id": member_id, "status": "published", "is_featured": True})
    return featured, researched, thoughtful
