"""Ranking metrics with binary relevance."""

from __future__ import annotations

import math
from collections.abc import Sequence


def first_relevant(relevance: Sequence[bool]) -> int | None:
    return next((i for i, rel in enumerate(relevance, start=1) if rel), None)


def hit_at_k(relevance: Sequence[bool], k: int) -> float:
    return 1.0 if any(relevance[:k]) else 0.0


def reciprocal_rank(relevance: Sequence[bool]) -> float:
    rank = first_relevant(relevance)
    return 1.0 / rank if rank else 0.0


def ndcg_at_k(relevance: Sequence[bool], k: int, total_relevant: int) -> float:
    """nDCG (Järvelin and Kekäläinen, 2002) with gains of 0 or 1."""
    dcg = sum(1.0 / math.log2(i + 1) for i, rel in enumerate(relevance[:k], start=1) if rel)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(k, total_relevant) + 1))
    return dcg / ideal if ideal else 0.0


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0
