"""Spaced repetition with the SM-2 algorithm (Wozniak, 1990).

A failed card comes back after ten minutes instead of one day, so it can
be practiced again in the same session.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from typing import Any

RELEARN_MINUTES = 10


@dataclass(frozen=True)
class Card:
    item_id: str
    due: str
    ease: float = 2.5
    interval: float = 0.0
    reps: int = 0
    lapses: int = 0

    @classmethod
    def new(cls, item_id: str, now: datetime) -> Card:
        return cls(item_id=item_id, due=now.isoformat(timespec="seconds"))

    def is_due(self, now: datetime) -> bool:
        return datetime.fromisoformat(self.due) <= now

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def grade_from_outcome(correct: bool, attempt: int, used_hint: bool = False) -> int:
    """Map an answer to an SM-2 grade from 0 to 5."""
    if not correct:
        return 1
    if attempt > 1 or used_hint:
        return 3
    return 5


def review(card: Card, grade: int, now: datetime) -> Card:
    if not 0 <= grade <= 5:
        raise ValueError("grade must be between 0 and 5")
    ease = max(1.3, card.ease + 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    if grade < 3:
        due = now + timedelta(minutes=RELEARN_MINUTES)
        return replace(
            card,
            ease=ease,
            interval=0.0,
            reps=0,
            lapses=card.lapses + 1,
            due=due.isoformat(timespec="seconds"),
        )
    if card.reps == 0:
        interval = 1.0
    elif card.reps == 1:
        interval = 6.0
    else:
        interval = round(card.interval * card.ease, 1)
    due = now + timedelta(days=interval)
    return replace(
        card,
        ease=ease,
        interval=interval,
        reps=card.reps + 1,
        due=due.isoformat(timespec="seconds"),
    )
