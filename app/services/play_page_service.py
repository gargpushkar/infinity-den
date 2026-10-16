from typing import Any
from urllib.parse import urlencode

from app.schemas.quiz import QuizItemRead
from app.services.quiz_service import QuizService, is_correct
from app.utils.markdown import render_markdown


async def claim_context(service: QuizService, item: QuizItemRead, *, answer: str) -> dict[str, Any]:
    """Everything the Fact or Fiction card needs, before or after answering."""
    correct = is_correct(item, answer)
    claim = {
        "claim": item.claim,
        "url": f"/play/{item.slug}",
        "fact_url": f"/play/{item.slug}?answer=fact",
        "fiction_url": f"/play/{item.slug}?answer=fiction",
        "next_url": f"/play?{urlencode({'after': item.slug})}",
        "is_answered": correct is not None,
    }
    if correct is not None:
        claim.update(
            {
                "is_correct": correct,
                "truth_label": "Fact" if item.is_true else "Fiction",
                "explanation_html": render_markdown(item.explanation),
                "article": await service.linked_article(item),
            }
        )
    return {"claim": claim}
