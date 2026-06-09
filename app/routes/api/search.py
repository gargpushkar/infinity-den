from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status

from app.schemas.article import ArticleSortField, SortDirection
from app.schemas.search import SearchQueryParams, SearchResponse
from app.services.search_service import SearchService, get_search_service


router = APIRouter(prefix="/api/search", tags=["Search"])


def get_public_search_service() -> SearchService:
    return get_search_service()


@router.get(
    "",
    response_model=SearchResponse,
    response_model_by_alias=False,
)
async def search_articles(
    q: str = Query(min_length=2, max_length=120),
    category: str | None = Query(default=None, max_length=120),
    tag: str | None = Query(default=None, max_length=64),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=12, ge=1, le=100),
    sort_by: ArticleSortField = Query(default="published_at"),
    sort_direction: SortDirection = Query(default="desc"),
    search_service: SearchService = Depends(get_public_search_service),
) -> SearchResponse:
    clean_query = q.strip()
    if len(clean_query) < 2:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Search query must contain at least 2 non-whitespace characters.",
        )

    query = SearchQueryParams(
        q=clean_query,
        category=category,
        tag=tag,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )

    return await search_service.search_articles(query)
