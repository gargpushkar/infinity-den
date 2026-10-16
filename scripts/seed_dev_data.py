"""Seed a development database with the six launch rooms and sample pieces.

Everything here is placeholder content for building and testing the site:
every piece is credited to "Sample writer", and the personal experiences are
illustrative, not real accounts. Replace it with real contributions before
launch.

The rooms come from LAUNCH_ROOMS in app/config/constants.py. Upserts by slug,
so rerunning is safe. Refuses to write to a database whose name does not end
in "_dev".

    python -m scripts.seed_dev_data            # preview, changes nothing
    python -m scripts.seed_dev_data --apply    # write
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.config.constants import LAUNCH_ROOMS
from app.config.settings import settings
from app.database.indexes import create_indexes
from app.database.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.models.article import ARTICLE_COLLECTION, create_article_document
from app.models.category import CATEGORY_COLLECTION, create_category_document
from app.models.question import QUESTION_COLLECTION, QuestionDocument
from app.models.quiz import QUIZ_COLLECTION
from app.models.tag import TAG_COLLECTION
from app.services.question_service import question_slug, site_today
from app.services.quiz_service import quiz_slug


NOW = datetime(2026, 10, 16, 8, 0, tzinfo=timezone.utc)
AUTHOR = "Sample writer"

ROOM_IMAGES: dict[str, str] = {
    "science": "/static/images/articles/search-traffic.svg",
    "psychology": "/static/images/articles/newsletter-loops.svg",
    "history": "/static/images/articles/content-engine.svg",
    "technology": "/static/images/articles/search-traffic.svg",
    "philosophy": "/static/images/articles/editorial-default.svg",
    "personal-stories": "/static/images/articles/contributors.svg",
}

ARTICLES: list[dict[str, Any]] = [
    # --- science -------------------------------------------------------------
    {
        "title": "Why the sky is blue and sunsets are red",
        "slug": "why-the-sky-is-blue-and-sunsets-are-red",
        "excerpt": "The same bit of physics paints the midday sky and the evening one, and it comes down to the size of air molecules.",
        "category_id": "science",
        "article_format": "article",
        "tags": ["Light", "Atmosphere"],
        "is_featured": True,
        "is_editors_pick": True,
        "days_ago": 2,
        "views": 1840,
        "sources": [
            {"title": "Rayleigh scattering (Wikipedia)", "url": "https://en.wikipedia.org/wiki/Rayleigh_scattering"},
            {"title": "Diffuse sky radiation (Wikipedia)", "url": "https://en.wikipedia.org/wiki/Diffuse_sky_radiation"},
        ],
        "body": [
            "Sunlight looks white, but it contains every colour of visible light. On its way to the ground it passes through air made mostly of nitrogen and oxygen molecules, which are far smaller than the wavelength of that light.",
            "Particles that small scatter short wavelengths much more strongly than long ones, roughly in proportion to one over the wavelength to the fourth power. This is Rayleigh scattering, named after the physicist Lord Rayleigh, who described it in the nineteenth century. Blue light is scattered several times more than red, so blue reaches your eyes from every part of the sky, not just from the direction of the sun.",
            "Violet light is scattered even more than blue, so why is the sky not violet? Sunlight contains less violet to begin with, some of it is absorbed high in the atmosphere, and human eyes are more sensitive to blue.",
            "At sunset the light reaches you at a low angle and travels through far more air. By the time it arrives, most of the blue has been scattered out of the direct beam, leaving the oranges and reds. Dust, smoke, and other particles can deepen those colours further.",
        ],
    },
    {
        "title": "The best place to look for life may be under the ice of Europa",
        "slug": "the-best-place-to-look-for-life-may-be-under-the-ice-of-europa",
        "excerpt": "Mars gets the headlines, but a frozen moon of Jupiter may hide a far larger ocean. Here is the case for looking there.",
        "category_id": "science",
        "article_format": "perspective",
        "is_speculative": True,
        "tags": ["Space", "Life"],
        "days_ago": 9,
        "views": 960,
        "body": [
            "When people talk about finding life beyond Earth, they usually mean Mars. I think the stronger bet is Europa, one of Jupiter's moons.",
            "Scientists believe Europa has a salty ocean of liquid water beneath its icy shell, possibly holding more water than all of Earth's oceans combined. Liquid water, a source of energy, and the right chemistry are the ingredients we associate with life, and Europa may have all three.",
            "The ice that makes Europa hard to explore may also protect whatever lies below it from the radiation that sterilises the surface. Mars, by contrast, has spent billions of years with very little liquid water on its surface.",
            "None of this means anything lives there. It is a hypothesis, and missions such as NASA's Europa Clipper are designed to tell us whether the moon is even habitable. But if I had to choose where to spend the next search, I would choose the ocean we cannot yet see.",
        ],
    },
    # --- psychology ----------------------------------------------------------
    {
        "title": "The Dunning-Kruger effect is more complicated than the meme",
        "slug": "the-dunning-kruger-effect-is-more-complicated-than-the-meme",
        "excerpt": "The famous confidence curve is not what the original study found, and researchers still debate how much of the effect is real.",
        "category_id": "psychology",
        "article_format": "article",
        "tags": ["Cognition", "Self-knowledge"],
        "is_editors_pick": True,
        "days_ago": 4,
        "views": 2310,
        "sources": [
            {"title": "Kruger & Dunning (1999), Unskilled and unaware of it", "url": "https://doi.org/10.1037/0022-3514.77.6.1121"},
            {"title": "Dunning-Kruger effect (Wikipedia)", "url": "https://en.wikipedia.org/wiki/Dunning%E2%80%93Kruger_effect"},
        ],
        "body": [
            "The internet version goes like this: the less you know, the more confident you are, until you learn enough to realise how little you know. It is usually drawn as a steep peak of confidence followed by a valley. That chart does not come from the original research.",
            "In 1999, Justin Kruger and David Dunning asked people to take tests of logic, grammar, and humour, then estimate how well they had done. Those who scored lowest tended to overestimate their performance by a wide margin, while top scorers slightly underestimated theirs. But low scorers still rated themselves below high scorers. They were not the most confident people in the room; they just could not see how far behind they were.",
            "Since then, critics have argued that part of this pattern can appear from statistics alone. Regression toward the mean, combined with the general tendency to rate ourselves as above average, can produce a similar-looking graph even when people's self-assessments are merely noisy rather than biased. Researchers still disagree about how much of the effect survives once those factors are accounted for.",
            "The more careful takeaway is less dramatic but more useful: judging our own skill is genuinely hard, especially in areas where we rarely get clear feedback.",
        ],
    },
    {
        "title": "What a year of journaling taught me about my moods",
        "slug": "what-a-year-of-journaling-taught-me-about-my-moods",
        "excerpt": "Three lines a night for a year, and what they showed me about memory, sleep, and the stories I tell myself.",
        "category_id": "psychology",
        "article_format": "experience",
        "tags": ["Habits", "Emotions"],
        "days_ago": 6,
        "views": 1210,
        "body": [
            "Last year I started writing three lines every night: what happened, how I felt, and one thing I noticed. I expected to give up within a month. I kept going because the entries started to surprise me.",
            "The first surprise was how badly I remembered my own weeks. Periods I would have described as awful turned out to have plenty of good days in them. My memory had kept the worst evening and quietly deleted the rest.",
            "The second was how often a bad mood followed a bad night of sleep. Not always, and I am wary of reading too much into one person's notebook, but the pattern was hard to ignore once it was written down.",
            "I do not think journaling fixed anything. What it gave me was a record I could argue with when my mind insisted that everything was always like this.",
        ],
    },
    # --- history -------------------------------------------------------------
    {
        "title": "The Library of Alexandria did not burn down in a single night",
        "slug": "the-library-of-alexandria-did-not-burn-down-in-a-single-night",
        "excerpt": "The popular story is one catastrophic fire. Most historians now describe something slower, and more familiar.",
        "category_id": "history",
        "article_format": "article",
        "tags": ["Ancient world", "Knowledge"],
        "is_featured": True,
        "days_ago": 3,
        "views": 1675,
        "sources": [
            {"title": "Library of Alexandria (Wikipedia)", "url": "https://en.wikipedia.org/wiki/Library_of_Alexandria"},
            {"title": "Library of Alexandria (Britannica)", "url": "https://www.britannica.com/topic/Library-of-Alexandria"},
        ],
        "body": [
            "The story most of us learned is simple: the greatest library of the ancient world went up in flames, and with it, centuries of knowledge. The real history is messier.",
            "The library was founded in Alexandria in the early third century BC under the Ptolemaic kings, and it became one of the largest collections of the ancient world. Scholars such as Eratosthenes, who estimated the circumference of the Earth, worked there.",
            "In 48 BC, during Julius Caesar's war in Alexandria, a fire spread through part of the city and may have destroyed some books. Ancient writers disagree about how much was lost, and the library seems to have continued afterwards.",
            "Most historians now describe a long decline rather than a single disaster: political purges that drove scholars away, shrinking support from the rulers who had funded it, and later fighting in the city that damaged the quarter where it stood. Knowledge, it turns out, is more often lost through neglect than through one dramatic night.",
        ],
    },
    {
        "title": "History class should teach how we know, not just what happened",
        "slug": "history-class-should-teach-how-we-know-not-just-what-happened",
        "excerpt": "Dates and names fade. The habit of asking where a claim comes from lasts a lifetime.",
        "category_id": "history",
        "article_format": "perspective",
        "tags": ["Learning", "Evidence"],
        "days_ago": 12,
        "views": 540,
        "body": [
            "Most of the history I was taught arrived as finished facts: this happened, on this date, for these reasons. Almost none of it explained how anyone knew.",
            "I think that is backwards. The facts matter, but the more valuable skill is the one historians actually use: asking who wrote a source, why, and what they could not have known.",
            "A student who can compare two conflicting accounts of the same event is better prepared for today's information than one who has memorised a list of battles. They will meet far more competing claims online than they ever will in an exam.",
            "Teach fewer dates if you have to. Teach people how to weigh evidence.",
        ],
    },
    # --- technology ----------------------------------------------------------
    {
        "title": "How large language models predict the next word",
        "slug": "how-large-language-models-predict-the-next-word",
        "excerpt": "Behind the fluent replies is a surprisingly simple goal, repeated billions of times.",
        "category_id": "technology",
        "article_format": "article",
        "tags": ["AI", "Language"],
        "is_featured": True,
        "days_ago": 1,
        "views": 2980,
        "sources": [
            {"title": "Vaswani et al. (2017), Attention Is All You Need", "url": "https://arxiv.org/abs/1706.03762"},
            {"title": "Large language model (Wikipedia)", "url": "https://en.wikipedia.org/wiki/Large_language_model"},
        ],
        "body": [
            "A large language model is trained on a vast amount of text with one basic goal: given what came before, predict what comes next. The unit it predicts is a token, which may be a whole word or just part of one.",
            "Each token is turned into a list of numbers. Most modern models use the transformer architecture, introduced in a 2017 paper called Attention Is All You Need. Its key idea, attention, lets every token weigh how relevant each other token in the passage is when building its representation.",
            "During training, the model's parameters, often billions of them, are adjusted again and again to reduce the gap between its predictions and the real text. Many models are then tuned further, often using human feedback, so they follow instructions and answer helpfully.",
            "When you ask a question, the model produces a probability for every possible next token, picks one, adds it to the text, and repeats. That is why the output can be fluent and still wrong: predicting plausible text is not the same as checking facts.",
        ],
    },
    {
        "title": "Soon, 'did a human write this?' will be the wrong question",
        "slug": "soon-did-a-human-write-this-will-be-the-wrong-question",
        "excerpt": "Most writing will be some mix of people and machines. What we should ask is who stands behind it.",
        "category_id": "technology",
        "article_format": "perspective",
        "is_speculative": True,
        "tags": ["AI", "Creativity"],
        "days_ago": 7,
        "views": 1430,
        "body": [
            "Today we ask whether a piece of writing was made by a person or a machine. I suspect that within a few years the question will stop being useful, because most writing will be both.",
            "People already draft with autocomplete, edit with grammar tools, and brainstorm with chatbots. The line between help and authorship is blurring, and detection tools are unreliable enough that they cannot settle it.",
            "A better question is accountability: who checked this, who stands behind its claims, and who will correct it if it is wrong? That is a question we can answer whether or not a machine was involved.",
            "This is a prediction, not a certainty. But if it is right, platforms should spend less energy guessing at origins and more on being transparent about responsibility.",
        ],
    },
    # --- philosophy ----------------------------------------------------------
    {
        "title": "The Ship of Theseus, and why it still matters",
        "slug": "the-ship-of-theseus-and-why-it-still-matters",
        "excerpt": "If every plank is replaced, is it still the same ship? A two-thousand-year-old puzzle about identity that has not gone away.",
        "category_id": "philosophy",
        "article_format": "article",
        "tags": ["Identity", "Thought experiments"],
        "is_editors_pick": True,
        "days_ago": 5,
        "views": 1590,
        "sources": [
            {"title": "Ship of Theseus (Wikipedia)", "url": "https://en.wikipedia.org/wiki/Ship_of_Theseus"},
            {"title": "Identity Over Time (Stanford Encyclopedia of Philosophy)", "url": "https://plato.stanford.edu/entries/identity-time/"},
        ],
        "body": [
            "Plutarch tells of the ship of the hero Theseus, kept by the Athenians for generations. As its planks rotted, they were replaced with new timber, until philosophers argued over whether it was still the same ship.",
            "Centuries later, Thomas Hobbes added a twist. Suppose someone collected every discarded plank and rebuilt the original. Now there are two ships. Which one is the ship of Theseus?",
            "There are several answers. Some say identity lies in the material, so the rebuilt ship wins. Others say it lies in continuous form and function, so the repaired ship wins. Others argue that 'the same' depends on what we are asking for: a museum and a navy might give different answers.",
            "The puzzle matters because it is not really about ships. Many of the cells in your body are replaced over the years, companies change every employee, and bands tour with none of their original members. Deciding what makes something the same thing over time is a question we answer, usually without noticing, every day.",
        ],
    },
    {
        "title": "Is being successful the same as being happy?",
        "slug": "is-being-successful-the-same-as-being-happy",
        "excerpt": "We often treat them as one goal. I think they pull in different directions more often than we admit.",
        "category_id": "philosophy",
        "article_format": "perspective",
        "tags": ["Happiness", "Meaning"],
        "days_ago": 10,
        "views": 870,
        "body": [
            "We talk about success and happiness as though one leads to the other. Get the job, the title, the recognition, and contentment will follow. I am not convinced.",
            "Success is usually measured against other people: rankings, salaries, promotions. Happiness seems to depend much more on things that do not rank well, such as time with people we love, work that feels meaningful, and enough rest.",
            "That does not make ambition bad. But it suggests that if we only chase the first, we should not be surprised when the second does not arrive with it.",
            "My own answer is that they overlap, but neither contains the other. What is yours?",
        ],
    },
    # --- personal-stories ----------------------------------------------------
    {
        "title": "What failure taught me about starting over",
        "slug": "what-failure-taught-me-about-starting-over",
        "excerpt": "The business I spent three years building closed in a week. What came after surprised me.",
        "category_id": "personal-stories",
        "article_format": "experience",
        "tags": ["Resilience", "Work"],
        "is_featured": True,
        "days_ago": 2,
        "views": 2150,
        "body": [
            "The small business I had spent three years building closed in a single week. A contract fell through, the money ran out, and that was that.",
            "For a while I treated it as proof that I had been foolish to try. What changed my mind was writing down, plainly, what I had actually learned: how to price my work, how to say no, and how quickly I could pick up skills when I had to.",
            "Starting again was not a triumphant comeback. It was a series of small, unglamorous steps, and it took longer than I wanted. But I started from a better place than the first time, because I knew more.",
            "This is one person's experience, not a formula. If there is a lesson, it is that a failure is easier to carry once you have named what it gave you.",
        ],
    },
    {
        "title": "A belief I used to hold but no longer do",
        "slug": "a-belief-i-used-to-hold-but-no-longer-do",
        "excerpt": "I was sure that some people were simply born unable to draw. Learning at thirty changed my mind.",
        "category_id": "personal-stories",
        "article_format": "experience",
        "tags": ["Belief", "Learning"],
        "days_ago": 8,
        "views": 1020,
        "body": [
            "For most of my life I believed that some people could draw and some could not, and that I was firmly in the second group.",
            "At thirty I signed up for an evening class mostly to prove the point. The first weeks were humbling. Then, slowly, my drawings started to look like the things I was looking at.",
            "Nothing magical happened. I learned to measure angles, to look at shapes instead of symbols, and to practise badly without stopping. The skill had been learnable all along; I had just never stayed with it long enough to find out.",
            "I still do not draw well. But I no longer assume I cannot learn something just because I am bad at it today.",
        ],
    },
]


# Question Room samples, dated relative to the day the seed runs so there is
# always a question for "today" (plus past ones and one upcoming).
QUESTIONS: list[dict[str, Any]] = [
    {"days_from_today": 0, "category_id": "philosophy", "text": "Can a person be intelligent without being wise?", "intro": "We often use the two words together. Are they really the same thing, or can you have one without the other?"},
    {"days_from_today": -1, "category_id": "personal-stories", "text": "What is something school never taught you but life did?", "intro": None},
    {"days_from_today": -2, "category_id": "technology", "text": "Should AI-generated work be considered original creativity?", "intro": "If a person shapes the prompt and picks the result, who is the author?"},
    {"days_from_today": -3, "category_id": "psychology", "text": "Is being successful the same as being happy?", "intro": None},
    {"days_from_today": 1, "category_id": "science", "text": "Which scientific discovery would you most like to see in your lifetime?", "intro": None},
]


# Fact or Fiction samples. Each explanation is short and true; most link to
# the sample article that goes deeper.
CLAIMS: list[dict[str, Any]] = [
    {"claim": "The sky is blue because it reflects the color of the ocean.", "is_true": False, "category_id": "science", "article_slug": "why-the-sky-is-blue-and-sunsets-are-red",
     "explanation": "The sky is blue because air molecules scatter short, blue wavelengths of sunlight far more than long, red ones. This is **Rayleigh scattering**, and it happens over deserts and mountains too."},
    {"claim": "Air scatters violet light even more strongly than blue light.", "is_true": True, "category_id": "science", "article_slug": "why-the-sky-is-blue-and-sunsets-are-red",
     "explanation": "Shorter wavelengths scatter more, so violet scatters most. The sky still looks blue because sunlight contains less violet, some is absorbed high in the atmosphere, and our eyes are more sensitive to blue."},
    {"claim": "The Library of Alexandria was wiped out by a single great fire.", "is_true": False, "category_id": "history", "article_slug": "the-library-of-alexandria-did-not-burn-down-in-a-single-night",
     "explanation": "A fire in 48 BC, during Julius Caesar's war in Alexandria, may have destroyed some books, but most historians describe a long decline over centuries rather than one disaster."},
    {"claim": "Large language models look up each answer in a database of verified facts.", "is_true": False, "category_id": "technology", "article_slug": "how-large-language-models-predict-the-next-word",
     "explanation": "They generate text by predicting the next token from patterns learned in training. That is why an answer can sound fluent and still be wrong."},
    {"claim": "Scientists think Jupiter's moon Europa has a liquid-water ocean beneath its ice.", "is_true": True, "category_id": "science", "article_slug": "the-best-place-to-look-for-life-may-be-under-the-ice-of-europa",
     "explanation": "Spacecraft measurements point to a salty ocean under Europa's icy shell, which is why missions such as NASA's _Europa Clipper_ were sent to study it."},
    {"claim": "In the original Dunning-Kruger study, the lowest scorers rated themselves higher than the top scorers did.", "is_true": False, "category_id": "psychology", "article_slug": "the-dunning-kruger-effect-is-more-complicated-than-the-meme",
     "explanation": "Low scorers overestimated how well they had done, but still rated themselves below high scorers. The famous confidence-peak chart does not come from the study."},
    {"claim": "The Ship of Theseus puzzle was recorded by the ancient writer Plutarch.", "is_true": True, "category_id": "philosophy", "article_slug": "the-ship-of-theseus-and-why-it-still-matters",
     "explanation": "Plutarch described the Athenians replacing the ship's rotting planks one by one, and philosophers arguing over whether it was still the same ship."},
    {"claim": "Humans use only 10% of their brains.", "is_true": False, "category_id": "psychology", "article_slug": None,
     "explanation": "Brain imaging shows activity across virtually the whole brain, though not all at once. Even simple tasks draw on many regions, and damage to almost any area has noticeable effects."},
]


def _tags() -> list[dict[str, str]]:
    names = sorted({tag for article in ARTICLES for tag in article["tags"]})
    return [{"name": name, "slug": name.lower().replace(" ", "-")} for name in names]


def _require_dev_database() -> None:
    if not settings.mongodb_db_name.endswith("_dev"):
        sys.exit(
            f"Refusing to seed '{settings.mongodb_db_name}': set MONGODB_DB_NAME "
            "to a development database ending in '_dev'."
        )


async def _preview(db: Any) -> None:
    print(f"Database: {settings.mongodb_db_name}")
    for room in LAUNCH_ROOMS:
        exists = await db[CATEGORY_COLLECTION].count_documents({"slug": room["slug"]})
        print(f"  room {room['slug']}: {'update' if exists else 'create'}")
    for article in ARTICLES:
        exists = await db[ARTICLE_COLLECTION].count_documents({"slug": article["slug"]})
        print(f"  article {article['slug']}: {'update' if exists else 'create'}")
    print("\nPreview only. Rerun with --apply to write.")


async def _apply(db: Any) -> None:
    for room in LAUNCH_ROOMS:
        document = create_category_document(
            name=str(room["name"]),
            slug=str(room["slug"]),
            subtitle=str(room["subtitle"]),
            description=str(room["description"]),
            image=ROOM_IMAGES.get(str(room["slug"])),
            nav_order=int(room["nav_order"]),
        ).to_mongo()
        await db[CATEGORY_COLLECTION].update_one(
            {"slug": document["slug"]}, {"$set": document}, upsert=True
        )
    print(f"Upserted {len(LAUNCH_ROOMS)} rooms.")

    tags = _tags()
    for tag in tags:
        await db[TAG_COLLECTION].update_one({"slug": tag["slug"]}, {"$set": tag}, upsert=True)
    print(f"Upserted {len(tags)} tags.")

    for article in ARTICLES:
        published_at = NOW - timedelta(days=article["days_ago"])
        document = create_article_document(
            title=article["title"],
            slug=article["slug"],
            excerpt=article["excerpt"],
            content="\n\n".join(article["body"]),
            author=AUTHOR,
            cover_image=ROOM_IMAGES.get(article["category_id"]),
            category_id=article["category_id"],
            tags=article["tags"],
            is_featured=article.get("is_featured", False),
            article_format=article["article_format"],
            is_editors_pick=article.get("is_editors_pick", False),
            is_speculative=article.get("is_speculative", False),
            sources=article.get("sources", []),
            status="published",
            published_at=published_at,
            views=article["views"],
        ).to_mongo()
        document["created_at"] = published_at
        document["updated_at"] = published_at
        await db[ARTICLE_COLLECTION].update_one(
            {"slug": article["slug"]}, {"$set": document}, upsert=True
        )
    print(f"Upserted {len(ARTICLES)} sample pieces.")

    today = date.fromisoformat(site_today())
    for question in QUESTIONS:
        publish_date = (today + timedelta(days=question["days_from_today"])).isoformat()
        document = QuestionDocument(
            text=question["text"],
            slug=question_slug(question["text"], publish_date),
            publish_date=publish_date,
            intro=question["intro"],
            category_id=question["category_id"],
            status="published",
        ).to_mongo()
        # Never displace a question an editor scheduled on that date.
        if await db[QUESTION_COLLECTION].count_documents(
            {"publish_date": publish_date, "text": {"$ne": question["text"]}}, limit=1
        ):
            print(f"  {publish_date} already has a question; skipped a sample.")
            continue
        # Keyed by text so reseeding on a later day moves each sample to its
        # new date instead of piling up copies.
        await db[QUESTION_COLLECTION].update_one({"text": question["text"]}, {"$set": document}, upsert=True)
    print(f"Sample questions seeded (today is {today} in {settings.site_timezone}).")

    for claim in CLAIMS:
        now = datetime.now(timezone.utc)
        # Keyed by claim text; the slug is set once so shared links keep working.
        await db[QUIZ_COLLECTION].update_one(
            {"claim": claim["claim"]},
            {
                "$set": {**claim, "status": "published", "updated_at": now},
                "$setOnInsert": {"slug": quiz_slug(claim["claim"]), "created_at": now},
            },
            upsert=True,
        )
    print(f"Upserted {len(CLAIMS)} Fact or Fiction claims.")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the changes.")
    args = parser.parse_args()

    _require_dev_database()
    await connect_to_mongo()
    try:
        db = get_database()
        if not args.apply:
            await _preview(db)
            return

        await _apply(db)
        await create_indexes()
        print("Indexes ensured. Seed complete.")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
