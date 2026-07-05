"""Unicode-aware tokenization.

The word pattern keeps letters like æ, ø and å inside a word, and keeps
hyphen or apostrophe joined words together ("e-mail", "Anna's").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

WORD_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-ZÆØÅ0-9])")
_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int

    @property
    def lower(self) -> str:
        return self.text.lower()


def tokenize(text: str) -> list[str]:
    """Return lowercased word tokens."""
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]


def tokens_with_spans(text: str) -> list[Token]:
    """Return tokens with their original case and character offsets."""
    return [Token(m.group(0), m.start(), m.end()) for m in WORD_RE.finditer(text)]


def normalize_space(text: str) -> str:
    return _SPACE.sub(" ", text).strip()


def sentences(text: str) -> list[str]:
    """Split text into sentences. Line breaks also end a sentence."""
    output: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        output.extend(part.strip() for part in _SENTENCE_END.split(line) if part.strip())
    return output
