"""BM25 index."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Collection, Mapping, Sequence


class BM25Index:
    """Okapi BM25 with two IDF variants.

    ``idf="legacy"`` is the formula used in LinguaPilot:
    log((N - df + 0.5) / (df + 0.5)). It turns negative for a term that is in
    more than half of the chunks, so a common word can push a good chunk
    down. ``idf="robertson"`` adds 1 inside the log (as Lucene does) and is
    never negative.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75, idf: str = "robertson") -> None:
        if idf not in {"legacy", "robertson"}:
            raise ValueError("idf must be 'legacy' or 'robertson'")
        self.k1 = k1
        self.b = b
        self.idf_mode = idf
        self._postings: dict[str, list[tuple[str, int]]] = {}
        self._lengths: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._avg_length = 1.0

    def build(self, documents: Mapping[str, Sequence[str]]) -> None:
        self._postings = {}
        self._lengths = {}
        for doc_id, terms in documents.items():
            self._lengths[doc_id] = len(terms)
            for term, tf in Counter(terms).items():
                self._postings.setdefault(term, []).append((doc_id, tf))
        count = len(self._lengths)
        self._avg_length = (sum(self._lengths.values()) / count) if count else 1.0
        self._avg_length = self._avg_length or 1.0
        self._idf = {term: self._compute_idf(count, len(p)) for term, p in self._postings.items()}

    def idf(self, term: str) -> float:
        return self._idf.get(term, 0.0)

    def search(
        self,
        terms: Sequence[str],
        top_k: int,
        allowed: Collection[str] | None = None,
    ) -> list[tuple[str, float]]:
        scores: dict[str, float] = {}
        for term, qtf in Counter(terms).items():
            idf = self._idf.get(term)
            if idf is None:
                continue
            for doc_id, tf in self._postings[term]:
                if allowed is not None and doc_id not in allowed:
                    continue
                norm = tf + self.k1 * (
                    1 - self.b + self.b * self._lengths[doc_id] / self._avg_length
                )
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * tf * (self.k1 + 1) / norm * qtf
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return ranked[:top_k]

    def _compute_idf(self, count: int, df: int) -> float:
        ratio = (count - df + 0.5) / (df + 0.5)
        if self.idf_mode == "legacy":
            return math.log(ratio)
        return math.log(1.0 + ratio)
