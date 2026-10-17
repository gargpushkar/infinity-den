from typing import Any
from urllib.parse import urlencode

from app.schemas.quiz import QuizItemRead
from app.services.quiz_service import QuizService, is_correct
from app.utils.markdown import render_markdown


async def claim_context(
    service: QuizService, item: QuizItemRead, *, answer: str, on_home: bool = False
) -> dict[str, Any]:
    """Everything the Fact or Fiction card needs, before or after answering.

    On the homepage the answer links reload the homepage at the card, so the
    claim is answered in place; on /play they stay on the claim's own page.
    """
    correct = is_correct(item, answer)
    if on_home:
        answer_url = f"/?claim={item.slug}&answer={{}}#arcade"  # slugs are URL-safe
        next_url = f"/?{urlencode({'after': item.slug})}#arcade"
    else:
        answer_url = f"/play/{item.slug}?answer={{}}"
        next_url = f"/play?{urlencode({'after': item.slug})}"
    claim = {
        "claim": item.claim,
        "url": f"/play/{item.slug}",
        "fact_url": answer_url.format("fact"),
        "fiction_url": answer_url.format("fiction"),
        "next_url": next_url,
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
