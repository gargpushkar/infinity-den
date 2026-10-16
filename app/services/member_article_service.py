"""Members writing their own pieces.

Members can save drafts and submit for review, never publish. They can edit
a piece while it is a draft or waiting for review; once published (or
archived) it is locked for them in Phase 1, so a reviewed piece cannot change
without an editor.
"""

import re
import secrets
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING

from app.config.constants import (
    ARTICLE_STATUS_DRAFT,
    ARTICLE_STATUS_PENDING_REVIEW,
    ARTICLE_STATUS_PUBLISHED,
)
from app.database.mongodb import get_database
from app.models.article import ARTICLE_COLLECTION, missing_required_sources
from app.models.category import CATEGORY_COLLECTION
from app.schemas.article import ArticleCreate, ArticleRead, ArticleUpdate, MemberPieceInput
from app.schemas.user import MemberRead
from app.services.article_service import SOURCES_REQUIRED_MESSAGE, ArticleService


MEMBER_EDITABLE_STATUSES = frozenset({ARTICLE_STATUS_DRAFT, ARTICLE_STATUS_PENDING_REVIEW})


class MemberArticleError(Exception):
    pass


class PieceNotFoundError(MemberArticleError):
    pass


class PieceLockedError(MemberArticleError):
    pass


class PieceInvalidError(MemberArticleError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


def piece_slug(title: str) -> str:
    """Readable and unique without a lookup: the title plus a short random tail."""
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60].strip("-") or "piece"
    return f"{base}-{secrets.token_hex(3)}"


class MemberArticleService:
    def __init__(self, database: AsyncIOMotorDatabase | None = None) -> None:
        self.database = database if database is not None else get_database()
        self.articles = ArticleService(database=self.database)

    async def list_own(self, member: MemberRead) -> list[ArticleRead]:
        cursor = (
            self.database[ARTICLE_COLLECTION]
            .find({"author_id": member.id})
            .sort([("updated_at", DESCENDING)])
            .limit(100)
        )
        return [ArticleRead.model_validate(document) async for document in cursor]

    async def get_own(self, member: MemberRead, article_id: str) -> ArticleRead:
        article = await self.articles.get_article_by_id(article_id)
        # Someone else's piece looks exactly like a missing one.
        if article is None or article.author_id != member.id:
            raise PieceNotFoundError("Piece was not found.")
        return article

    async def save(
        self,
        member: MemberRead,
        payload: MemberPieceInput,
        *,
        submit: bool,
        article_id: str | None = None,
    ) -> ArticleRead:
        if not await self.database[CATEGORY_COLLECTION].count_documents(
            {"slug": payload.category_id}, limit=1
        ):
            raise PieceInvalidError("category_id", "Choose a room.")
        # Catch a missing source when the member submits, rather than leaving
        # it for the editor to bounce back.
        if submit and missing_required_sources(
            article_format=payload.article_format,
            status=ARTICLE_STATUS_PUBLISHED,
            sources=payload.sources,
        ):
            raise PieceInvalidError("sources", SOURCES_REQUIRED_MESSAGE)

        status = ARTICLE_STATUS_PENDING_REVIEW if submit else ARTICLE_STATUS_DRAFT
        fields: dict[str, Any] = {
            **payload.model_dump(),
            "status": status,
            "author": member.display_name,
        }

        if article_id is None:
            return await self.articles.create_article(
                ArticleCreate(**fields, slug=piece_slug(payload.title), author_id=member.id)
            )

        existing = await self.get_own(member, article_id)
        if existing.status not in MEMBER_EDITABLE_STATUSES:
            raise PieceLockedError(
                "Published pieces can't be edited here. Ask an editor for changes."
            )
        if submit:
            fields["review_note"] = None  # resubmitting answers the editor's note

        return await self.articles.update_article(article_id, ArticleUpdate(**fields))


def parse_sources(text: str) -> list[dict[str, str]]:
    """One source per line, "Title | URL" or a bare URL (same as the admin editor)."""
    sources = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        title, divider, url = line.rpartition("|")
        if not divider:
            title, url = line, line
        sources.append({"title": title.strip() or url.strip(), "url": url.strip()})
    return sources


def sources_text(sources: list[Any]) -> str:
    return "\n".join(
        f"{source['title']} | {source['url']}" if isinstance(source, dict) else f"{source.title} | {source.url}"
        for source in sources
    )
