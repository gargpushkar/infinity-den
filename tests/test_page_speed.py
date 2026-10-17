"""Room and tag counts take one query however many rooms and tags exist.

They used to take one query per row, which made /articles and search slow on a
remote database and slower with every new tag.
"""

import asyncio

import pytest

from app.models.article import ARTICLE_COLLECTION
from app.models.category import CATEGORY_COLLECTION
from app.models.tag import TAG_COLLECTION
from app.services import article_page_service, search_page_service
from tests.fakes import FakeCollection


class CountingCollection(FakeCollection):
    def __init__(self, documents=()):
        super().__init__(documents)
        self.queries = 0

    def find(self, *args, **kwargs):
        self.queries += 1
        return super().find(*args, **kwargs)

    def aggregate(self, *args, **kwargs):
        self.queries += 1
        return super().aggregate(*args, **kwargs)

    async def count_documents(self, *args, **kwargs):
        self.queries += 1
        return await super().count_documents(*args, **kwargs)


def _database(tag_count: int) -> dict:
    tags = [{"name": f"Tag {n}", "slug": f"tag-{n}"} for n in range(tag_count)]
    articles = [
        {"slug": "a", "status": "published", "category_id": "science", "tags": ["Tag 0", "Tag 1"]},
        {"slug": "b", "status": "published", "category_id": "science", "tags": ["Tag 0"]},
        {"slug": "c", "status": "draft", "category_id": "history", "tags": ["Tag 1"]},
    ]
    rooms = [{"name": "Cosmic Canvas", "slug": "science"}, {"name": "Echoes of Time", "slug": "history"}]
    return {
        ARTICLE_COLLECTION: CountingCollection(articles),
        CATEGORY_COLLECTION: FakeCollection(rooms),
        TAG_COLLECTION: FakeCollection(tags),
    }


@pytest.mark.parametrize("module", [article_page_service, search_page_service], ids=["articles", "search"])
def test_option_counts_are_one_query_whatever_the_number_of_tags(module):
    queries = []
    for tag_count in (3, 30):
        database = _database(tag_count)
        tags = asyncio.run(module._get_tag_options(database))
        rooms = asyncio.run(module._get_category_options(database))
        queries.append(database[ARTICLE_COLLECTION].queries)
    assert queries == [2, 2]  # one grouped count for rooms, one for tags

    # And the counts are still right: drafts don't count.
    assert {tag["name"]: tag["total"] for tag in tags}["Tag 0"] == 2
    assert {tag["name"]: tag["total"] for tag in tags}["Tag 1"] == 1
    assert {room["slug"]: room["total"] for room in rooms} == {"science": 2, "history": 0}
