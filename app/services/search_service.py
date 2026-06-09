import re

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.models.tag import TAG_COLLECTION
from app.schemas.article import ArticleQueryParams
from app.schemas.search import SearchArticleResult, SearchQueryParams, SearchResponse
from app.services.article_service import ArticleService


class SearchService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database
        self.article_service = ArticleService(database=database)

    async def search_articles(self, query: SearchQueryParams) -> SearchResponse:
        tag_filter = await self._resolve_tag_filter(query.tag)
        article_query = ArticleQueryParams(
            page=query.page,
            per_page=query.per_page,
            status=ARTICLE_STATUS_PUBLISHED,
            category_id=query.category,
            tag=tag_filter["name"] if tag_filter else None,
            search=query.q,
            sort_by=query.sort_by,
            sort_direction=query.sort_direction,
        )
        articles = await self.article_service.list_articles(article_query)

        return SearchResponse(
            query=query.q,
            category=query.category,
            tag=tag_filter["slug"] if tag_filter else None,
            items=[
                SearchArticleResult.from_article(article)
                for article in articles.items
            ],
            total=articles.total,
            page=articles.page,
            per_page=articles.per_page,
            total_pages=articles.total_pages,
            sort_by=articles.sort_by,
            sort_direction=articles.sort_direction,
            has_next=articles.has_next,
            has_previous=articles.has_previous,
            next_page=articles.next_page,
            previous_page=articles.previous_page,
        )

    async def _resolve_tag_filter(self, value: str | None) -> dict[str, str] | None:
        if value is None:
            return None

        clean_value = value.strip()
        if not clean_value:
            return None

        database = self.database
        if database is None:
            database = self.article_service.database

        normalized_value = clean_value.lower()
        escaped_value = re.escape(clean_value)
        tag = await database[TAG_COLLECTION].find_one(
            {
                "$or": [
                    {"slug": normalized_value},
                    {"name": {"$regex": f"^{escaped_value}$", "$options": "i"}},
                ]
            },
            {"_id": 0, "name": 1, "slug": 1},
        )
        if tag:
            return {
                "name": str(tag.get("name", clean_value)).strip(),
                "slug": str(tag.get("slug", normalized_value)).strip(),
            }

        return {"name": clean_value, "slug": normalized_value}


def get_search_service(
    database: AsyncIOMotorDatabase | None = None,
) -> SearchService:
    return SearchService(database=database)
