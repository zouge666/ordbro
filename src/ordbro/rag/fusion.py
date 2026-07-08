"""Reciprocal Rank Fusion (Cormack et al., 2009)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def rrf(
    rankings: Mapping[str, Sequence[tuple[str, float]]],
    k: int = 60,
    top_k: int | None = None,
) -> list[tuple[str, float]]:
    """Merge ranked lists. Each item adds 1 / (k + rank) to its score.

    Ties are broken by id so the result is stable, as in LinguaPilot.
    """
    scores: dict[str, float] = {}
    for ranking in rankings.values():
        for rank, (item_id, _) in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    fused = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return fused[:top_k] if top_k is not None else fused
