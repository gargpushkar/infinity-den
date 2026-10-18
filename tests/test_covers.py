"""Generated covers: valid, stable, on-palette, and never echo the URL."""

import asyncio
import re
import xml.etree.ElementTree as ElementTree

import pytest
from fastapi import HTTPException

from app.routes.public.covers import cover
from app.routes.public.seo import social_image_url
from app.utils.covers import COVER_VERSION, PATTERNS, cover_svg, resolve_cover


PALETTE = {"#171a2b", "#c2562f", "#f2a33a", "#fbf7f0", "#8e3b1e", "#3a3f5c", "#1f2337",
           "#6f8ca8", "#9db7ce"}  # the Debate Den's dusk blues, for the "against" side


@pytest.mark.parametrize("room", sorted(PATTERNS))
def test_every_room_draws_a_valid_on_palette_svg(room):
    svg = cover_svg(room, "the-ship-of-theseus-and-why-it-still-matters")
    root = ElementTree.fromstring(svg)
    assert root.get("viewBox") == "0 0 640 360"
    assert len(root.findall("{http://www.w3.org/2000/svg}polygon")) > 3
    assert set(re.findall(r"#[0-9a-f]{6}", svg)) <= PALETTE


def test_same_article_same_cover_different_articles_differ():
    assert cover_svg("history", "a") == cover_svg("history", "a")
    assert cover_svg("history", "a") != cover_svg("history", "b")


def test_slug_is_never_written_into_the_svg():
    assert "zqx-marker" not in cover_svg("science", "zqx-marker-article")


def test_uploaded_cover_wins_and_placeholders_are_ignored():
    generated = f"/covers/science/sky.svg?v={COVER_VERSION}"
    assert resolve_cover("https://images.nasa.gov/x.jpg", "science", "sky") == "https://images.nasa.gov/x.jpg"
    assert resolve_cover(None, "science", "sky") == generated
    assert resolve_cover("/static/images/articles/search-traffic.svg", "science", "sky") == generated
    # Rooms without their own pattern still get a cover.
    assert resolve_cover(None, "business", "old-piece").startswith("/covers/psychology/old-piece.svg")


def test_cover_route_serves_cacheable_svg_and_rejects_unknown_rooms():
    response = asyncio.run(cover(room="philosophy", slug="identity"))
    assert response.media_type == "image/svg+xml"
    assert "immutable" in response.headers["cache-control"]
    with pytest.raises(HTTPException) as error:
        asyncio.run(cover(room="business", slug="identity"))
    assert error.value.status_code == 404


def test_svg_covers_are_not_used_as_social_previews():
    # Facebook, LinkedIn and X ignore SVG; "" makes the page use the branded PNG.
    assert social_image_url(None, f"/covers/science/sky.svg?v={COVER_VERSION}") == ""
    assert social_image_url(None, "https://example.org/photo.jpg") == "https://example.org/photo.jpg"
