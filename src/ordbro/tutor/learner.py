"""Learner state, saved as one JSON file per learner on the local machine.

Nothing leaves the computer. There are no accounts and no passwords.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ordbro.tutor.srs import Card

_ID = re.compile(r"^[a-z0-9_-]{1,40}$")
HISTORY_LIMIT = 300


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class LearnerState:
    learner_id: str
    created_at: str = field(default_factory=lambda: utc_now().isoformat(timespec="seconds"))
    mastery: dict[str, float] = field(default_factory=dict)
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    cards: dict[str, Card] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)

    def record(self, event: dict[str, Any]) -> None:
        self.history.append(event)
        if len(self.history) > HISTORY_LIMIT:
            del self.history[: len(self.history) - HISTORY_LIMIT]
        skill = event.get("skill")
        if skill and event.get("final", True):
            counts = self.counts.setdefault(skill, {"seen": 0, "correct": 0})
            counts["seen"] += 1
            counts["correct"] += int(bool(event.get("correct")))

    def recent_skills(self, size: int = 3) -> list[str]:
        return [e["skill"] for e in self.history[-size:] if e.get("skill")]

    def due_cards(self, now: datetime) -> list[Card]:
        return sorted(
            (card for card in self.cards.values() if card.is_due(now)),
            key=lambda card: card.due,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "learner_id": self.learner_id,
            "created_at": self.created_at,
            "mastery": self.mastery,
            "counts": self.counts,
            "cards": {key: card.to_dict() for key, card in self.cards.items()},
            "history": self.history,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LearnerState:
        return cls(
            learner_id=data["learner_id"],
            created_at=data.get("created_at", utc_now().isoformat(timespec="seconds")),
            mastery={k: float(v) for k, v in data.get("mastery", {}).items()},
            counts=data.get("counts", {}),
            cards={k: Card(**v) for k, v in data.get("cards", {}).items()},
            history=data.get("history", []),
            settings=data.get("settings", {}),
        )


class LearnerStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path(self, learner_id: str) -> Path:
        if not _ID.match(learner_id):
            raise ValueError("learner id may only use a-z, 0-9, '-' and '_'")
        return self.directory / f"{learner_id}.json"

    def load(self, learner_id: str) -> LearnerState:
        path = self.path(learner_id)
        if not path.exists():
            return LearnerState(learner_id=learner_id)
        with path.open(encoding="utf-8") as handle:
            return LearnerState.from_dict(json.load(handle))

    def save(self, state: LearnerState) -> None:
        path = self.path(state.learner_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".learner-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, ensure_ascii=False, indent=1)
        os.replace(tmp, path)

    def reset(self, learner_id: str) -> LearnerState:
        path = self.path(learner_id)
        if path.exists():
            path.unlink()
        return LearnerState(learner_id=learner_id)
