from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi import status as http_status
from fastapi.templating import Jinja2Templates
from pymongo.errors import PyMongoError

from app.config.settings import settings
from app.services.nav_service import get_nav_context
from app.services.play_page_service import claim_context
from app.services.quiz_service import QuizService


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/play")
async def play(request: Request, after: str | None = Query(default=None, max_length=120)):
    """A random claim; `after` is the one just played, so it isn't repeated."""
    try:
        service = QuizService()
        item = await service.random_published(exclude_slug=after)
        context = await claim_context(service, item, answer="") if item else {"claim": None}
    except (RuntimeError, PyMongoError):
        context = {"claim": None, "is_unavailable": True}
    return await _render(request, context, title="Fact or Fiction")


@router.get("/play/{slug}")
async def play_claim(
    request: Request,
    slug: str = Path(min_length=3, max_length=120),
    answer: str = Query(default="", max_length=10),
):
    service = QuizService()
    item = await service.get_published(slug)
    if item is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Claim was not found.")
    return await _render(request, await claim_context(service, item, answer=answer), title=item.claim)


async def _render(request: Request, context: dict[str, Any], *, title: str):
    claim = context.get("claim")
    return templates.TemplateResponse(
        request,
        "pages/play.html",
        {
            **await get_nav_context(request),
            **context,
            "app_name": settings.app_name,
            "page_title": title,
            "seo_title": f"Fact or fiction: {claim['claim']}" if claim else "Fact or Fiction",
            "seo_description": "Decide whether a surprising claim is true, then see why.",
            # Revealed answers are for the person who clicked; index the question only.
            "robots": "noindex, follow" if claim and claim["is_answered"] else "index, follow",
        },
    )
