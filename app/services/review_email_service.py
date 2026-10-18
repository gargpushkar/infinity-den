"""Telling writers how the review of their piece went.

Called from ArticleService.update_article, the one path every status change
takes (the review buttons and the full editor alike). Editorial pieces have
no author_id and get no email.
"""

import logging
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from app.config.constants import ARTICLE_STATUS_DRAFT, ARTICLE_STATUS_PUBLISHED
from app.config.settings import settings
from app.models.user import USER_COLLECTION
from app.services.email_service import EmailError, send_email


logger = logging.getLogger(__name__)


async def notify_review_outcome(database: Any, old_status: str | None, article: dict[str, Any], update: dict[str, Any]) -> None:
    """Email the author when an editor publishes their piece or sends it back with a note."""
    published = old_status != ARTICLE_STATUS_PUBLISHED and article.get("status") == ARTICLE_STATUS_PUBLISHED
    # Only an editor's send-back sets a note; a member saving their own draft never does.
    sent_back = article.get("status") == ARTICLE_STATUS_DRAFT and bool(update.get("review_note"))
    if not (published or sent_back) or not article.get("author_id"):
        return
    try:
        author = await database[USER_COLLECTION].find_one({"_id": ObjectId(article["author_id"]), "is_active": True})
    except InvalidId:
        return
    if author is None:
        return

    site = settings.site_url.rstrip("/")
    title = article.get("title", "your piece")
    if published:
        subject = f"Your piece is published on {settings.app_name}"
        body = (
            f"Hi {author['display_name']},\n\n"
            f"An editor has published \"{title}\". Readers can find it here:\n\n"
            f"{site}/articles/{article['slug']}\n\n"
            f"Thank you for writing for {settings.app_name}.\n\n{settings.app_name}\n"
        )
    else:
        subject = "Your piece needs a few changes"
        body = (
            f"Hi {author['display_name']},\n\n"
            f"An editor read \"{title}\" and sent it back with a note:\n\n"
            f"{update['review_note']}\n\n"
            f"Edit it here, then submit it again when you're ready:\n\n"
            f"{site}/write/{article['_id']}\n\n{settings.app_name}\n"
        )
    try:
        await send_email(author["email"], subject, body)
    except EmailError:
        logger.exception("Could not send a review email")
