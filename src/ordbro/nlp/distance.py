"""Edit distance, word alignment, WER and CER."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass


def levenshtein(a: Sequence, b: Sequence) -> int:
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, item_a in enumerate(a, start=1):
        current = [i]
        for j, item_b in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (item_a != item_b),
                )
            )
        previous = current
    return previous[-1]


def similarity(a: str, b: str) -> float:
    """1.0 for equal strings, 0.0 for nothing in common."""
    if not a and not b:
        return 1.0
    return 1.0 - levenshtein(a, b) / max(len(a), len(b))


@dataclass(frozen=True)
class Step:
    op: str  # "match", "sub", "del" (missing in hyp) or "ins" (extra in hyp)
    ref: int | None
    hyp: int | None


def align(
    ref: Sequence[str],
    hyp: Sequence[str],
    sub_cost: Callable[[str, str], float] | None = None,
) -> list[Step]:
    """Align two token lists with the smallest total cost.

    ``sub_cost`` returns a cost in [0, 1] for replacing one token with
    another. The default is 0 for equal tokens and 1 otherwise. A soft cost
    lets similar words ("hedder" and "heder") line up with each other.
    """
    cost = sub_cost or (lambda x, y: 0.0 if x == y else 1.0)
    n, m = len(ref), len(hyp)
    table = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        table[i][0] = float(i)
    for j in range(1, m + 1):
        table[0][j] = float(j)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            table[i][j] = min(
                table[i - 1][j - 1] + cost(ref[i - 1], hyp[j - 1]),
                table[i - 1][j] + 1.0,
                table[i][j - 1] + 1.0,
            )
    steps: list[Step] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            step_cost = cost(ref[i - 1], hyp[j - 1])
            if abs(table[i][j] - (table[i - 1][j - 1] + step_cost)) < 1e-9:
                op = "match" if ref[i - 1] == hyp[j - 1] else "sub"
                steps.append(Step(op, i - 1, j - 1))
                i, j = i - 1, j - 1
                continue
        if i > 0 and abs(table[i][j] - (table[i - 1][j] + 1.0)) < 1e-9:
            steps.append(Step("del", i - 1, None))
            i -= 1
        else:
            steps.append(Step("ins", None, j - 1))
            j -= 1
    steps.reverse()
    return steps


def wer(ref: Sequence[str], hyp: Sequence[str]) -> float:
    """Word error rate. An empty reference gives 0 or 1."""
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(list(ref), list(hyp)) / len(ref)


def cer(ref: str, hyp: str) -> float:
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(ref, hyp) / len(ref)
