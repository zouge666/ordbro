"""Choosing exercises and giving feedback in two steps.

The first wrong answer gives a hint and a second try. The learner then has
to think about the rule again (an elicitation prompt). The second wrong
answer shows the right answer with a short explanation and, when there is
one, the passage from the course notes that explains the rule.
"""

from __future__ import annotations

import random
import zlib
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from ordbro.content.lexicon import Lexicon
from ordbro.exercises.checking import check_answer
from ordbro.exercises.models import Exercise
from ordbro.tutor.learner import LearnerState
from ordbro.tutor.policy import TutorPolicy
from ordbro.tutor.srs import Card, grade_from_outcome, review

Explainer = Callable[[Exercise], dict[str, Any] | None]

_PRAISE = ("Right!", "Correct!", "Well done!", "Yes, that is it!")
RECENT_WINDOW = 15


@dataclass
class Feedback:
    exercise_id: str
    skill: str
    correct: bool
    attempt: int
    final: bool
    message: str
    hint: str = ""
    answer: str = ""
    explanation: str = ""
    note: str = ""
    close: bool = False
    source: dict[str, Any] | None = None
    mastery_before: float | None = None
    mastery_after: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExerciseEngine:
    def __init__(
        self,
        exercises: list[Exercise],
        policy: TutorPolicy,
        lexicon: Lexicon | None = None,
        explainer: Explainer | None = None,
        seed: int | None = None,
    ) -> None:
        self.items = {item.id: item for item in exercises}
        self.policy = policy
        self.lexicon = lexicon
        self.explainer = explainer
        self.rng = random.Random(seed)
        self.by_skill: dict[str, list[Exercise]] = {}
        for item in exercises:
            if item.skill:
                self.by_skill.setdefault(item.skill, []).append(item)
        self.cards = [item for item in exercises if item.card_id]
        self._card_order = list(dict.fromkeys(item.card_id for item in self.cards))

    def get(self, exercise_id: str) -> Exercise:
        try:
            return self.items[exercise_id]
        except KeyError:
            raise KeyError(f"unknown exercise: {exercise_id}") from None

    # choosing ---------------------------------------------------------------

    def next(
        self,
        state: LearnerState,
        now: datetime,
        focus: str | None = None,
    ) -> tuple[Exercise | None, str]:
        """Return the next exercise and why it was chosen."""
        if focus == "review":
            return self.next_review(state, now), "review"
        if focus and focus in self.by_skill:
            return self.for_skill(state, focus), "chosen skill"
        recent_types = [e.get("type") for e in state.history[-3:]]
        if (
            state.due_cards(now)
            and "flashcard" not in recent_types
            and "translate" not in recent_types
        ):
            return self.next_review(state, now), "words due for review"
        skill = self.policy.next_skill(state)
        if skill is None:
            return self.next_review(state, now), "all skills mastered"
        return self.for_skill(state, skill.id), "adaptive"

    def for_skill(self, state: LearnerState, skill_id: str, mode: str | None = None) -> Exercise:
        mode = mode or self.policy.mode_for(self.policy.mastery(state, skill_id))
        pool = self.by_skill.get(skill_id, [])
        if not pool:
            raise KeyError(f"no exercises for skill '{skill_id}'")
        recent = {e.get("exercise") for e in state.history[-RECENT_WINDOW:]}
        fresh = [item for item in pool if item.id not in recent] or pool
        preferred = [item for item in fresh if item.mode == mode]
        return self.rng.choice(preferred or fresh)

    def next_review(self, state: LearnerState, now: datetime) -> Exercise | None:
        due = state.due_cards(now)
        if due:
            card = due[0]
            direction = "da-en" if card.reps < 2 else "en-da"
            return self._card_item(card.item_id, direction)
        for card_id in self._card_order:
            if card_id not in state.cards:
                return self._card_item(card_id, "da-en")
        return None

    def _card_item(self, card_id: str, direction: str) -> Exercise | None:
        pos, _, word = card_id.partition(":")
        return self.items.get(f"card:{direction}:{pos}:{word}")

    # answering --------------------------------------------------------------

    def answer(
        self,
        state: LearnerState,
        exercise_id: str,
        answer: str,
        attempt: int,
        now: datetime,
    ) -> Feedback:
        item = self.get(exercise_id)
        attempt = max(1, attempt)
        is_known = self.lexicon.is_known if self.lexicon else None
        verdict = check_answer(answer, item.answers, is_known)
        final = verdict.correct or attempt >= 2
        feedback = Feedback(
            exercise_id=item.id,
            skill=item.skill,
            correct=verdict.correct,
            attempt=attempt,
            final=final,
            message="",
            note=verdict.note,
            close=verdict.close,
        )
        if attempt == 1 and item.skill and self.policy.graph.has(item.skill):
            feedback.mastery_before = round(self.policy.mastery(state, item.skill), 4)
            after = self.policy.update(state, item.skill, verdict.correct, item.guess)
            feedback.mastery_after = round(after, 4)
        if final and item.card_id:
            card = state.cards.get(item.card_id) or Card.new(item.card_id, now)
            state.cards[item.card_id] = review(
                card, grade_from_outcome(verdict.correct, attempt), now
            )
        state.record(
            {
                "ts": now.isoformat(timespec="seconds"),
                "exercise": item.id,
                "skill": item.skill,
                "type": item.type,
                "correct": verdict.correct,
                "attempt": attempt,
                "final": final,
            }
        )
        if verdict.correct:
            feedback.message = _PRAISE[zlib.crc32(item.id.encode()) % len(_PRAISE)]
            feedback.explanation = item.explanation
        elif not final:
            feedback.message = "Almost. Check the spelling." if verdict.close else "Not quite yet."
            feedback.hint = item.hint or _default_hint(item)
        else:
            feedback.message = "Here is the answer."
            feedback.answer = item.answers[0]
            feedback.explanation = item.explanation
        if final and self.explainer is not None and item.skill:
            feedback.source = self.explainer(item)
        return feedback


def _default_hint(item: Exercise) -> str:
    first = item.answers[0]
    if item.type in {"choice", "flashcard"}:
        return "Read the sentence again and look at the words around the gap."
    if " " in first.strip():
        return f"The answer has {len(first.split())} words."
    return f"The answer starts with '{first[0]}'."
