"""Day and night colour tokens keep text readable (WCAG AA: 4.5:1 for text)."""

import re
from pathlib import Path

import pytest


CSS = Path("app/static/css/main.css").read_text()

# (text token, background token) pairs the templates actually use.
TEXT_PAIRS = [
    ("text", "bg-main"), ("text", "card"), ("text", "bg-secondary"),
    ("text-secondary", "bg-main"), ("text-secondary", "card"), ("text-secondary", "bg-secondary"),
    ("text-muted", "bg-main"), ("text-muted", "card"),
    ("accent", "bg-main"), ("accent", "card"), ("accent", "bg-secondary"), ("accent", "accent-tint"),
    ("on-action", "action"), ("on-action", "action-hover"),
    ("label-experience", "card"), ("label-experience", "bg-main"),
    ("success", "success-bg"), ("danger", "danger-bg"), ("warning-fg", "warning-bg"),
    ("header-muted", "header-bg"), ("amber", "header-bg"), ("ivory", "header-bg"),
]


def _block(start: str) -> str:
    i = CSS.index(start)
    return CSS[i: CSS.index("\n}\n", i)]


def _tokens(*blocks: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for block in blocks:
        tokens.update(dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", block)))
    return tokens


def _resolve(tokens: dict[str, str], name: str) -> str:
    value = tokens[name].strip()
    for _ in range(5):  # a token that points at itself would loop forever
        if not value.startswith("var(--"):
            return value
        value = tokens[value[6:-1]].strip()
    raise AssertionError(f"--{name} does not resolve to a colour")


def _luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i: i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


DAY = _tokens(_block(":root {"))
NIGHT = {**DAY, **_tokens(_block("@media (prefers-color-scheme: dark) {\n  :root {"))}


@pytest.mark.parametrize("mode", [DAY, NIGHT], ids=["day", "night"])
@pytest.mark.parametrize(("text", "background"), TEXT_PAIRS)
def test_text_tokens_meet_aa(mode, text, background):
    ratio = _contrast(_resolve(mode, text), _resolve(mode, background))
    assert ratio >= 4.5, f"{text} on {background}: {ratio:.2f}:1"
