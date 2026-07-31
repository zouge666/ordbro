"""Learner feedback: saved as JSON lines and summarized for the teacher.

The summary turns ratings into concrete suggestions, for example which
skill feels too hard or which questions did not get a useful answer.
"""

from __future__ import annotations

import json
import threading
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MIN_RATINGS = 3


class FeedbackStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def add(self, event: dict[str, Any]) -> dict[str, Any]:
        record = {"ts": datetime.now(UTC).isoformat(timespec="seconds"), **event}
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def summary(self) -> dict[str, Any]:
        return summarize(self.all())


def summarize(events: list[dict[str, Any]]) -> dict[str, Any]:
    helpful: dict[str, Counter[str]] = defaultdict(Counter)
    difficulty: dict[str, Counter[str]] = defaultdict(Counter)
    unanswered: list[str] = []
    for event in events:
        kind = event.get("kind", "other")
        if event.get("helpful") is not None:
            helpful[kind]["yes" if event["helpful"] else "no"] += 1
            if kind == "ask" and not event["helpful"]:
                unanswered.append(event.get("comment") or event.get("target_id", ""))
        if event.get("difficulty") and event.get("skill"):
            difficulty[event["skill"]][event["difficulty"]] += 1

    suggestions: list[str] = []
    for skill, counts in sorted(difficulty.items()):
        total = sum(counts.values())
        if total < MIN_RATINGS:
            continue
        if counts["hard"] / total >= 0.5:
            suggestions.append(
                f"Many learners find '{skill}' hard. Add more recognition items "
                "or start this skill with a lower mastery estimate."
            )
        elif counts["easy"] / total >= 0.6:
            suggestions.append(f"'{skill}' looks easy. The tutor can move on sooner.")
    for kind, counts in sorted(helpful.items()):
        total = counts["yes"] + counts["no"]
        if total >= MIN_RATINGS and counts["yes"] / total < 0.6:
            suggestions.append(f"Explanations for '{kind}' are often not helpful. Review them.")
    if unanswered:
        suggestions.append(
            f"{len(unanswered)} questions did not get a useful answer. "
            "Add the topic to the course notes or the glossary."
        )
    return {
        "total": len(events),
        "helpful": {kind: dict(counts) for kind, counts in helpful.items()},
        "difficulty": {skill: dict(counts) for skill, counts in difficulty.items()},
        "unanswered": unanswered[-20:],
        "suggestions": suggestions,
    }
