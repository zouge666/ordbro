"""The skill graph: CEFR level, prerequisites and linked course notes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    name_da: str
    level: str
    about: str = ""
    requires: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)


class SkillGraph:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = skills
        self._by_id = {skill.id: skill for skill in skills}
        for skill in skills:
            for required in skill.requires:
                if required not in self._by_id:
                    raise ValueError(f"skill '{skill.id}' requires unknown skill '{required}'")
        self._check_acyclic()

    @classmethod
    def load(cls, path: Path) -> SkillGraph:
        with path.open(encoding="utf-8") as handle:
            raw = json.load(handle)
        return cls(
            [
                Skill(
                    id=item["id"],
                    name=item["name"],
                    name_da=item["name_da"],
                    level=item["level"],
                    about=item.get("about", ""),
                    requires=tuple(item.get("requires", [])),
                    notes=tuple(item.get("notes", [])),
                )
                for item in raw
            ]
        )

    def __iter__(self):
        return iter(self.skills)

    def __len__(self) -> int:
        return len(self.skills)

    def get(self, skill_id: str) -> Skill:
        return self._by_id[skill_id]

    def has(self, skill_id: str) -> bool:
        return skill_id in self._by_id

    def unlocked(self, mastery: dict[str, float], threshold: float, default: float) -> list[Skill]:
        return [
            skill
            for skill in self.skills
            if all(mastery.get(req, default) >= threshold for req in skill.requires)
        ]

    def _check_acyclic(self) -> None:
        state: dict[str, int] = {}

        def visit(skill_id: str) -> None:
            if state.get(skill_id) == 1:
                raise ValueError(f"skill graph has a cycle at '{skill_id}'")
            if state.get(skill_id) == 2:
                return
            state[skill_id] = 1
            for required in self._by_id[skill_id].requires:
                visit(required)
            state[skill_id] = 2

        for skill in self.skills:
            visit(skill.id)
