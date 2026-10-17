"""Policy pages render and are discoverable; corrections are dated and editor-only;
no request goes to Google for fonts."""

import asyncio
from datetime import datetime
from pathlib import Path

import pytest

from app.middleware.security_headers import CONTENT_SECURITY_POLICY
from app.routes.public import pages
from app.routes.public.pages import POLICY_PAGES
from app.schemas.article import ArticleUpdate
from tests.test_member_publishing import _input, _member, _service, _stored
from tests.test_theme_switch import _Request


class _PageRequest(_Request):
    def __init__(self, path: str) -> None:
        super().__init__({})
        self.url = type("URL", (), {"path": path, "__str__": lambda s: path})()


@pytest.mark.parametrize("path", list(POLICY_PAGES))
def test_policy_pages_render_with_the_contact_address(path, monkeypatch):
    async def nav(_request):
        return {"nav_rooms": [], "contact_email": "editors@infinityden.test", "current_member": None}

    monkeypatch.setattr(pages, "get_nav_context", nav)
    captured = {}
    monkeypatch.setattr(pages.templates, "TemplateResponse", lambda request, name, context: captured.update(name=name, context=context))
    asyncio.run(pages.policy_page(_PageRequest(path)))
    html = pages.templates.get_template(captured["name"]).render(request=_PageRequest(path), **captured["context"])
    assert POLICY_PAGES[path]["title"] in html and 'aria-current="page"' in html
    if path != "/editorial-policy":
        assert "mailto:editors@infinityden.test" in html


def test_footer_links_every_policy_page():
    footer = Path("app/templates/partials/footer.html").read_text()
    assert all(f'href="{path}"' in footer for path in POLICY_PAGES)


def test_fonts_never_come_from_google():
    assert "google" not in CONTENT_SECURITY_POLICY
    assert "google" not in Path("app/templates/layouts/base.html").read_text()
    for font in ("newsreader-latin.woff2", "poppins-400-latin.woff2", "OFL.txt"):
        assert Path("app/static/fonts", font).exists()


def test_correction_note_is_dated_when_it_changes():
    members = _service()
    article_id = asyncio.run(members.save(_member(), _input(), submit=False)).id
    service = members.articles
    corrected = asyncio.run(service.update_article(article_id, ArticleUpdate(correction_note="An earlier version gave the wrong year.")))
    stamp = corrected.corrected_at
    assert isinstance(stamp, datetime)

    # Saving again with the same note keeps the original date.
    again = asyncio.run(service.update_article(article_id, ArticleUpdate(correction_note="An earlier version gave the wrong year.", title="New title")))
    assert again.corrected_at == stamp

    cleared = asyncio.run(service.update_article(article_id, ArticleUpdate(correction_note="  ")))
    assert cleared.correction_note is None and cleared.corrected_at is None


def test_members_cannot_write_correction_notes():
    service = _service()
    piece = asyncio.run(service.save(_member(), _input(), submit=False))
    _stored(service)[0]["correction_note"] = "Editor's note"
    asyncio.run(service.save(_member(), _input(), submit=False, article_id=piece.id))
    assert _stored(service)[0]["correction_note"] == "Editor's note"
