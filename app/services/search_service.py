from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.constants import ARTICLE_STATUS_PUBLISHED
from app.schemas.article import ArticleQueryParams
from app.schemas.search import SearchArticleResult, SearchQueryParams, SearchResponse
from app.services.article_service import ArticleService


class SearchService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.article_service = ArticleService(database=database)

    async def search_articles(self, query: SearchQueryParams) -> SearchResponse:
        article_query = ArticleQueryParams(
            page=query.page,
            per_page=query.per_page,
            status=ARTICLE_STATUS_PUBLISHED,
            search=query.q,
            sort_by=query.sort_by,
            sort_direction=query.sort_direction,
        )
        articles = await self.article_service.list_articles(article_query)

        return SearchResponse(
            query=query.q,
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


def get_search_service(
    database: AsyncIOMotorDatabase | None = None,
) -> SearchService:
    return SearchService(database=database)
