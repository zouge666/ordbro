from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

TYPE_MODE = {
    "choice": "recognize",
    "flashcard": "recognize",
    "cloze": "recall",
    "form": "recall",
    "order": "produce",
    "translate": "produce",
}
GUESS_TYPED = 0.05


@dataclass(frozen=True)
class Exercise:
    id: str
    skill: str
    type: str
    prompt: str
    answers: tuple[str, ...]
    text: str = ""
    options: tuple[str, ...] = ()
    tokens: tuple[str, ...] = ()
    hint: str = ""
    explanation: str = ""
    level: str = "A1"
    card_id: str = ""
    speak: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def mode(self) -> str:
        return TYPE_MODE.get(self.type, "recall")

    @property
    def guess(self) -> float:
        """Chance of a right answer without knowing the skill."""
        if self.options:
            return 1.0 / len(self.options)
        if self.type == "order" and self.tokens:
            return 1.0 / max(2, len(self.tokens) * (len(self.tokens) - 1))
        return GUESS_TYPED

    def public(self) -> dict[str, Any]:
        """What the learner sees. Answers stay on the server."""
        data = asdict(self)
        for key in ("answers", "explanation", "hint", "tags"):
            data.pop(key)
        data["mode"] = self.mode
        data["has_hint"] = bool(self.hint)
        return data


def from_dict(data: dict[str, Any]) -> Exercise:
    values = dict(data)
    for key in ("answers", "options", "tokens", "tags"):
        if key in values:
            values[key] = tuple(values[key])
    exercise = Exercise(**values)
    if exercise.type not in TYPE_MODE:
        raise ValueError(f"{exercise.id}: unknown exercise type '{exercise.type}'")
    if not exercise.answers:
        raise ValueError(f"{exercise.id}: no answers")
    if exercise.options and not set(exercise.answers) <= set(exercise.options):
        raise ValueError(f"{exercise.id}: the answer is not one of the options")
    return exercise


def load_bank(path: Path) -> list[Exercise]:
    with path.open(encoding="utf-8") as handle:
        items = [from_dict(item) for item in json.load(handle)]
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("exercise ids must be unique")
    return items
