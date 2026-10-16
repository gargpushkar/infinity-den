"""The small markdown subset the editors support, rendered safely.

Mirrors renderMarkdownPreview in app/static/js/main.js line for line, so the
editor preview and the published page always match. Keep the two in step.

Safe by construction: every line is HTML-escaped *before* any formatting is
applied, and links are only created for http(s) URLs. Raw HTML in the input
therefore always comes out as visible text, never as markup.

Supported: ## and ### headings, - lists, > quotes, **bold**, _italic_,
`code`, and [text](https://link). Each other non-empty line is a paragraph.
"""

import re
from html import escape

from markupsafe import Markup


_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"_([^_]+)_")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def _format(html: str) -> str:
    html = _CODE.sub(r"<code>\1</code>", html)
    html = _BOLD.sub(r"<strong>\1</strong>", html)
    return _ITALIC.sub(r"<em>\1</em>", html)


def _inline(text: str) -> str:
    # Links are found first and their URLs left untouched, so an underscore
    # in a URL never turns into <em> and breaks the link.
    html = escape(text, quote=True)
    parts: list[str] = []
    position = 0
    for match in _LINK.finditer(html):
        parts.append(_format(html[position:match.start()]))
        parts.append(
            f'<a href="{match.group(2)}" target="_blank" rel="noopener noreferrer nofollow">'
            f"{_format(match.group(1))}</a>"
        )
        position = match.end()
    parts.append(_format(html[position:]))
    return "".join(parts)


def render_markdown(text: str) -> Markup:
    blocks: list[str] = []
    list_items: list[str] = []

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            flush_list()
        elif stripped.startswith("- "):
            list_items.append(_inline(stripped[2:]))
        else:
            flush_list()
            if stripped.startswith("### "):
                blocks.append(f"<h3>{_inline(stripped[4:])}</h3>")
            elif stripped.startswith("## "):
                blocks.append(f"<h2>{_inline(stripped[3:])}</h2>")
            elif stripped.startswith("> "):
                blocks.append(f"<blockquote>{_inline(stripped[2:])}</blockquote>")
            else:
                blocks.append(f"<p>{_inline(stripped)}</p>")
    flush_list()

    # Markup tells Jinja this string is already safe; it is, because every
    # piece of user text above went through escape() first.
    return Markup("".join(blocks))
