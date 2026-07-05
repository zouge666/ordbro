"""Analyzers turn text into index terms and query terms.

``LegacyAnalyzer`` copies the behaviour of the LinguaPilot RAG
infrastructure, so results can be compared with the original pipeline.
``DanishAnalyzer`` is the version used by Ordbro.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Iterable
from typing import Protocol

from ordbro.nlp.danish import (
    DANISH_STOPWORDS,
    ENGLISH_STOPWORDS,
    CompoundSplitter,
    DanishStemmer,
)
from ordbro.nlp.tokenize import WORD_RE

# Same pattern and stop list as linguapilot-rag-infrastructure (query_processor.py,
# sparse_encoder.py and bm25_indexer.py).
LEGACY_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
LEGACY_STOPWORDS = frozenset(
    """
    the and for with that this from are was were what when where which who whom how why
    into about your you a an is of to in on
    """.split()
)

# Danish grammar words that are also English stop words. They are kept in
# English questions because learners ask about them ("when do I use at?").
_KEEP_IN_ENGLISH = frozenset({"at", "i", "for", "under", "over", "to", "her", "man", "som"})
_DANISH_MARKERS = frozenset(
    "hvad hvordan hvornår hvorfor hvem hvilken hvilket hvilke jeg du er og ikke bruger "
    "man det den der som har kan skal vil må".split()
)
_QUOTED = re.compile(r"[\"'‘’“”«»]([^\"'‘’“”«»]{1,40})[\"'‘’“”«»]")
_ASCII_SPELLINGS = (("aa", "å"), ("ae", "æ"), ("oe", "ø"))


class Analyzer(Protocol):
    name: str

    def fit(self, texts: Iterable[str]) -> None: ...

    def index_terms(self, text: str) -> list[str]: ...

    def query_terms(self, text: str) -> list[str]: ...


class LegacyAnalyzer:
    """ASCII tokenizer, English stop words, no stemming."""

    name = "legacy"

    def fit(self, texts: Iterable[str]) -> None:
        return None

    def index_terms(self, text: str) -> list[str]:
        return [token.lower() for token in LEGACY_TOKEN_RE.findall(text)]

    def query_terms(self, text: str) -> list[str]:
        raw = [token.lower() for token in LEGACY_TOKEN_RE.findall(text)]
        keywords: list[str] = []
        for token in raw:
            if len(token) < 2 or token in LEGACY_STOPWORDS or token in keywords:
                continue
            keywords.append(token)
        if keywords:
            return keywords
        fallback = list(dict.fromkeys(raw))
        if fallback:
            return fallback
        compact = text.strip().lower()
        return [compact] if compact else []


class DanishAnalyzer:
    """Unicode tokens, Snowball stems and compound parts.

    Query handling:
    * English questions lose their English stop words, Danish questions keep
      all words (BM25 already gives common words a low weight).
    * A capital "I" alone is the English pronoun; a lower case "i" is the
      Danish preposition.
    * Quoted words count twice.
    * "ae", "oe" and "aa" are read as æ, ø and å when only that spelling is
      a known word, so learners without a Danish keyboard are not punished.
    """

    name = "danish"

    def __init__(self, stem: bool = True, split_compounds: bool = True) -> None:
        self.stem = stem
        self.split_compounds = split_compounds
        self._stemmer = DanishStemmer()
        self._splitter = CompoundSplitter()
        self._known: set[str] = set()

    def fit(self, texts: Iterable[str]) -> None:
        words: list[str] = []
        for text in texts:
            words.extend(match.group(0).lower() for match in WORD_RE.finditer(text))
        self._splitter.fit(words)
        self._known = set(words)

    def index_terms(self, text: str) -> list[str]:
        terms: list[str] = []
        for match in WORD_RE.finditer(text):
            terms.extend(self._expand(match.group(0).lower()))
        return terms

    def query_terms(self, text: str) -> list[str]:
        tokens = [match.group(0) for match in WORD_RE.finditer(text)]
        if not tokens:
            return []
        english = guess_language(tokens) == "en"
        quoted = {m.lower() for q in _QUOTED.findall(text) for m in WORD_RE.findall(q)}
        terms: list[str] = []
        for original in tokens:
            token = original.lower()
            if english and _is_english_filler(original, token) and token not in quoted:
                continue
            token = self.fix_ascii(token)
            expanded = self._expand(token)
            terms.extend(expanded)
            if token in quoted:
                terms.extend(expanded)
        return terms

    def fix_ascii(self, token: str) -> str:
        if not self._known or token in self._known:
            return token
        for candidate in _ascii_variants(token):
            if candidate in self._known:
                return candidate
        return token

    def _expand(self, token: str) -> list[str]:
        output = [self._stemmer.stem(token) if self.stem else token]
        if self.split_compounds:
            for part in self._splitter.split(token):
                output.append(self._stemmer.stem(part) if self.stem else part)
        return output


def guess_language(tokens: list[str]) -> str:
    """Very small heuristic: is a query Danish or English?"""
    danish = english = 0
    for original in tokens:
        token = original.lower()
        if any(ch in token for ch in "æøå") or token in _DANISH_MARKERS:
            danish += 1
        elif original == "I" or (token in ENGLISH_STOPWORDS and token not in DANISH_STOPWORDS):
            english += 1
    return "da" if danish > english else "en"


def _is_english_filler(original: str, token: str) -> bool:
    if original == "I":
        return True
    return token in ENGLISH_STOPWORDS and token not in _KEEP_IN_ENGLISH


def _ascii_variants(token: str) -> list[str]:
    spots = [
        (i, pair, letter)
        for pair, letter in _ASCII_SPELLINGS
        for i in range(len(token) - 1)
        if token[i : i + 2] == pair
    ]
    if not spots or len(spots) > 4:
        return []
    variants: list[str] = []
    for size in range(1, len(spots) + 1):
        for combo in itertools.combinations(spots, size):
            positions = [i for i, _, _ in combo]
            if any(b - a < 2 for a, b in itertools.pairwise(sorted(positions))):
                continue
            chars = list(token)
            for i, _, letter in sorted(combo, reverse=True):
                chars[i : i + 2] = [letter]
            variants.append("".join(chars))
    return variants
