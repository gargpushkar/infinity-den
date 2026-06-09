from __future__ import annotations

from dataclasses import dataclass
from math import ceil
import re


DEFAULT_WORDS_PER_MINUTE = 220
WORD_PATTERN = re.compile(r"\b[\w'-]+\b")


@dataclass(frozen=True, slots=True)
class ReadingTime:
    word_count: int
    minutes: int

    @property
    def label(self) -> str:
        return f"{self.minutes} min read"


def calculate_reading_time(
    content: str,
    *,
    words_per_minute: int = DEFAULT_WORDS_PER_MINUTE,
) -> ReadingTime:
    clean_content = str(content or "")
    word_count = len(WORD_PATTERN.findall(clean_content))
    safe_words_per_minute = max(1, words_per_minute)
    minutes = max(1, ceil(word_count / safe_words_per_minute))

    return ReadingTime(word_count=word_count, minutes=minutes)
