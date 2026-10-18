"""Covers drawn from the logo: squares nested 15 degrees apart, in its four colours.

Each room has its own pattern, and the article's slug picks the variation, so
the same article always gets the same cover and nothing has to be uploaded.
The slug only seeds the random numbers; it is never written into the SVG.
"""

import hashlib
import math
import random
from collections.abc import Callable

INK = "#171a2b"
COPPER = "#c2562f"
AMBER = "#f2a33a"
IVORY = "#fbf7f0"
DEEP_COPPER = "#8e3b1e"
SLATE = "#3a3f5c"
NIGHT_SURFACE = "#1f2337"
# The Debate Den's cool side, against the logo's warm one.
DUSK = "#6f8ca8"
DUSK_LIGHT = "#9db7ce"

WIDTH, HEIGHT = 640, 360
STEP = math.pi / 12  # 15 degrees
SHRINK = 1 / (math.cos(STEP) + math.sin(STEP))  # a square turned 15 degrees inside the last one

# Bump when the drawing changes, so year-long browser caches pick up new covers.
COVER_VERSION = 1

# The old placeholder illustrations; any cover still pointing at them is ignored.
PLACEHOLDER_PREFIX = "/static/images/articles/"

Paint = Callable[[int, str, int], str]


def _corners(cx: float, cy: float, size: float, angle: float) -> str:
    radius = size / math.sqrt(2)
    points = []
    for quarter in (1, 3, 5, 7):
        turn = angle + quarter * math.pi / 4
        points.append(f"{cx + radius * math.cos(turn):.1f},{cy + radius * math.sin(turn):.1f}")
    return " ".join(points)


def _nest(cx: float, cy: float, size: float, layers: int, angle: float, direction: int, paint: Paint) -> str:
    shapes = []
    for layer in range(layers):
        shapes.append(paint(layer, _corners(cx, cy, size, angle), layers))
        size *= SHRINK
        angle += direction * STEP
    return "".join(shapes)


def _outline(points: str, colour: str, width: float = 2, opacity: float = 1, css_class: str = "") -> str:
    class_attr = f' class="{css_class}"' if css_class else ""
    return (
        f'<polygon{class_attr} points="{points}" fill="none" stroke="{colour}" '
        f'stroke-width="{width}" stroke-opacity="{opacity:.2f}"/>'
    )


def _thirds(layer: int, layers: int, outer: str, middle: str, inner: str) -> str:
    if layer < layers / 3:
        return outer
    return middle if layer < 2 * layers / 3 else inner


def _science(r: random.Random) -> tuple[str, str]:
    """A night sky of small dens around one deep one."""
    art = []
    for _ in range(22 + r.randrange(14)):
        colour = AMBER if r.random() < 0.3 else IVORY
        opacity = 0.35 + r.random() * 0.5
        art.append(_nest(r.random() * WIDTH, r.random() * HEIGHT, 4 + r.random() * 10, 2, r.random() * STEP * 6, 1,
                         lambda _l, p, _n, c=colour, o=opacity: _outline(p, c, 1.2, o)))
    art.append(_nest(WIDTH * (0.58 + r.random() * 0.3), HEIGHT * (0.3 + r.random() * 0.4), HEIGHT * (1 + r.random() * 0.5),
                     9, r.random() * STEP * 6, r.choice((1, -1)),
                     lambda l, p, n: _outline(p, _thirds(l, n, SLATE, COPPER, AMBER))))
    return INK, "".join(art)


def _psychology(r: random.Random) -> tuple[str, str]:
    """One long spiral turning inward."""
    def paint(layer: int, points: str, layers: int) -> str:
        if layer < layers / 3:
            return _outline(points, INK, 1.8, 0.55, "base")
        return _outline(points, _thirds(layer, layers, INK, COPPER, AMBER), 1.8)

    art = _nest(WIDTH * (0.35 + r.random() * 0.3), HEIGHT * (0.35 + r.random() * 0.3), WIDTH * (0.9 + r.random() * 0.3),
                15, r.random() * STEP * 6, r.choice((1, -1)), paint)
    return "paper", art


def _history(r: random.Random) -> tuple[str, str]:
    """The same shape repeating and fading, like a memory."""
    art = []
    size, x, angle = HEIGHT * (0.75 + r.random() * 0.2), WIDTH * (0.1 + r.random() * 0.08), r.random() * STEP * 6
    y, echoes = HEIGHT * (0.42 + r.random() * 0.16), 5 + r.randrange(3)
    for echo in range(echoes):
        opacity = 1 - echo * (0.8 / echoes)
        art.append(_nest(x, y, size, 3, angle, 1,
                         lambda l, p, _n, o=opacity: _outline(p, AMBER if l == 2 else IVORY, 1.8, o)))
        x += size * 0.42
        size *= 0.86
        angle += STEP
    return DEEP_COPPER, "".join(art)


def _technology(r: random.Random) -> tuple[str, str]:
    """A grid of squares, each turned a different number of 15-degree steps."""
    art, cell = [], 40
    offset_x, offset_y = -r.random() * cell, -r.random() * cell
    y = offset_y
    while y < HEIGHT + cell:
        x = offset_x
        while x < WIDTH + cell:
            roll, points = r.random(), _corners(x, y, 24, r.randrange(6) * STEP)
            if roll < 0.07:
                art.append(f'<polygon points="{points}" fill="{AMBER}"/>')
            else:
                art.append(_outline(points, COPPER if roll < 0.22 else SLATE, 1.6 if roll < 0.22 else 1.4))
            x += cell
        y += cell
    return INK, "".join(art)


def _philosophy(r: random.Random) -> tuple[str, str]:
    """Two spirals turning in opposite directions over one centre."""
    cy, size = HEIGHT * (0.45 + r.random() * 0.1), HEIGHT * (1.05 + r.random() * 0.25)
    gap, angle = WIDTH * (0.1 + r.random() * 0.08), r.random() * STEP * 6

    def left(layer: int, points: str, layers: int) -> str:
        if layer >= layers - 2:
            return _outline(points, AMBER, 1.8, 0.85)
        return _outline(points, INK, 1.8, 0.85, "base")

    def right(layer: int, points: str, layers: int) -> str:
        return _outline(points, AMBER if layer >= layers - 2 else COPPER, 1.8, 0.9)

    art = _nest(WIDTH / 2 - gap, cy, size, 10, angle, 1, left) + _nest(WIDTH / 2 + gap, cy, size, 10, -angle, -1, right)
    return "paper", art


def _personal_stories(r: random.Random) -> tuple[str, str]:
    """The logo's own filled layers, warm and close."""
    fills = (IVORY, COPPER, AMBER)
    art = _nest(WIDTH * (0.5 + r.random() * 0.3), HEIGHT * (0.38 + r.random() * 0.3), WIDTH * (0.95 + r.random() * 0.35),
                12, r.random() * STEP * 6, r.choice((1, -1)),
                lambda l, p, _n: f'<polygon points="{p}" fill="{fills[l % 3]}"/>')
    return AMBER, art


def _debate(r: random.Random) -> tuple[str, str]:
    """Two dens facing each other across a gap: warm for, cool against."""
    cy, size = HEIGHT * (0.46 + r.random() * 0.08), HEIGHT * (0.95 + r.random() * 0.2)
    gap, angle = WIDTH * (0.17 + r.random() * 0.04), r.random() * STEP * 6

    def warm(layer: int, points: str, layers: int) -> str:
        return _outline(points, AMBER if layer % 2 else COPPER, 2.2, 0.95)

    def cool(layer: int, points: str, layers: int) -> str:
        return _outline(points, DUSK_LIGHT if layer % 2 else DUSK, 2.2, 0.95)

    art = _nest(WIDTH / 2 - gap, cy, size, 9, angle, 1, warm) + _nest(WIDTH / 2 + gap, cy, size, 9, -angle, -1, cool)
    return INK, art


PATTERNS: dict[str, Callable[[random.Random], tuple[str, str]]] = {
    "science": _science,
    "psychology": _psychology,
    "history": _history,
    "technology": _technology,
    "philosophy": _philosophy,
    "personal-stories": _personal_stories,
    "debate": _debate,  # not a room: every debate's cover, at /covers/debate/{slug}.svg
}
# Rooms without their own pattern yet share the single inward spiral.
DEFAULT_PATTERN = "psychology"

# Light covers switch to the dark surface at night; the coloured ones keep their colours.
NIGHT_STYLE = (
    "<style>.paper{fill:%s}@media (prefers-color-scheme:dark){.paper{fill:%s}.base{stroke:%s}}</style>"
    % (IVORY, NIGHT_SURFACE, IVORY)
)


def cover_pattern(room: str | None) -> str:
    return room if room in PATTERNS else DEFAULT_PATTERN


def cover_svg(room: str, slug: str) -> str:
    seed = int.from_bytes(hashlib.sha256(f"{room}:{slug}".encode()).digest()[:8], "big")
    background, art = PATTERNS[room](random.Random(seed))
    if background == "paper":
        backdrop = f'{NIGHT_STYLE}<rect class="paper" width="{WIDTH}" height="{HEIGHT}"/>'
    else:
        backdrop = f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{background}"/>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'preserveAspectRatio="xMidYMid slice">{backdrop}{art}</svg>'
    )


def cover_url(room: str | None, slug: str) -> str:
    return f"/covers/{cover_pattern(room)}/{slug}.svg?v={COVER_VERSION}"


def resolve_cover(cover_image: str | None, room: str | None, slug: str) -> str:
    """An uploaded cover wins; otherwise (or for an old placeholder) the generated one."""
    if cover_image and not cover_image.startswith(PLACEHOLDER_PREFIX):
        return cover_image
    return cover_url(room, slug)
