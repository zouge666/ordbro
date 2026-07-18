"""Choosing what to practice next.

The policy follows two ideas from learning research:

* Practice should be hard but possible. The tutor picks the open skill
  whose predicted success is closest to a target (70 % by default).
* Support fades as the learner gets better. Low mastery gives
  recognition tasks (multiple choice), middle mastery gives recall tasks
  (fill in the gap), and high mastery gives production tasks (build or
  translate a sentence).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ordbro.tutor.bkt import BKTParams, predict_correct, update_mastery
from ordbro.tutor.learner import LearnerState
from ordbro.tutor.skills import Skill, SkillGraph

MODES = ("recognize", "recall", "produce")


@dataclass
class TutorPolicy:
    graph: SkillGraph
    params: BKTParams = BKTParams()
    target: float = 0.7
    mastered_at: float = 0.95
    unlock_at: float = 0.6
    max_repeat: int = 3

    def mastery(self, state: LearnerState, skill_id: str) -> float:
        return state.mastery.get(skill_id, self.params.p_init)

    def open_skills(self, state: LearnerState) -> list[Skill]:
        unlocked = self.graph.unlocked(state.mastery, self.unlock_at, self.params.p_init)
        return [s for s in unlocked if self.mastery(state, s.id) < self.mastered_at]

    def next_skill(self, state: LearnerState, exclude: tuple[str, ...] = ()) -> Skill | None:
        candidates = [s for s in self.open_skills(state) if s.id not in exclude]
        if not candidates:
            return None
        recent = state.recent_skills(self.max_repeat)
        blocked = recent[0] if len(recent) == self.max_repeat and len(set(recent)) == 1 else None
        if blocked and len(candidates) > 1:
            candidates = [s for s in candidates if s.id != blocked]
        order = {skill.id: index for index, skill in enumerate(self.graph)}
        return min(
            candidates,
            key=lambda s: (
                round(
                    abs(predict_correct(self.mastery(state, s.id), self.params) - self.target), 6
                ),
                order[s.id],
            ),
        )

    def mode_for(self, p_known: float) -> str:
        if p_known < 0.4:
            return "recognize"
        if p_known < 0.7:
            return "recall"
        return "produce"

    def update(self, state: LearnerState, skill_id: str, correct: bool, guess: float) -> float:
        before = self.mastery(state, skill_id)
        after = update_mastery(before, correct, self.params, guess=guess)
        state.mastery[skill_id] = round(after, 6)
        return after

    def daily_plan(self, state: LearnerState, now: datetime, size: int = 3) -> dict[str, Any]:
        due = state.due_cards(now)
        focus: list[Skill] = []
        excluded: list[str] = []
        while len(focus) < size:
            skill = self.next_skill(state, exclude=tuple(excluded))
            if skill is None:
                break
            focus.append(skill)
            excluded.append(skill.id)
        mastered = [s.id for s in self.graph if self.mastery(state, s.id) >= self.mastered_at]
        return {
            "due_reviews": len(due),
            "focus": [
                {
                    "id": s.id,
                    "name": s.name,
                    "name_da": s.name_da,
                    "level": s.level,
                    "about": s.about,
                    "mastery": round(self.mastery(state, s.id), 3),
                    "mode": self.mode_for(self.mastery(state, s.id)),
                }
                for s in focus
            ],
            "speaking": self.mastery(state, "pronunciation") < self.mastered_at,
            "mastered": mastered,
            "minutes": 5 + 2 * len(focus) + min(len(due), 10),
        }
