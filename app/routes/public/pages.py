"""Community guidelines, editorial policy, privacy policy, and terms.

The text lives in the templates so every change is in git. Change "updated"
whenever a page's meaning changes.
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config.settings import settings
from app.services.nav_service import get_nav_context


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

POLICY_PAGES = {
    "/guidelines": {
        "title": "Community guidelines",
        "template": "pages/policy_guidelines.html",
        "updated": "October 17, 2026",
        "description": "How we talk to each other on Infinity Den: critique arguments, not people.",
    },
    "/editorial-policy": {
        "title": "Editorial policy",
        "template": "pages/policy_editorial.html",
        "updated": "October 17, 2026",
        "description": "How editors review pieces, and our rules on sources, plagiarism, AI, and corrections.",
    },
    "/privacy": {
        "title": "Privacy policy",
        "template": "pages/policy_privacy.html",
        "updated": "October 18, 2026",
        "description": "What Infinity Den stores about you, why, who else sees it, and your rights.",
    },
    "/terms": {
        "title": "Terms of use",
        "template": "pages/policy_terms.html",
        "updated": "October 18, 2026",
        "description": "The terms for reading, joining, and writing on Infinity Den.",
    },
}


@router.get("/guidelines")
@router.get("/editorial-policy")
@router.get("/privacy")
@router.get("/terms")
async def policy_page(request: Request):
    page = POLICY_PAGES[request.url.path]
    return templates.TemplateResponse(
        request,
        page["template"],
        {
            **await get_nav_context(request),
            "app_name": settings.app_name,
            "page_title": page["title"],
            "seo_title": page["title"],
            "seo_description": page["description"],
            "updated": page["updated"],
            "policy_pages": [{"url": url, "title": p["title"]} for url, p in POLICY_PAGES.items()],
        },
    )
