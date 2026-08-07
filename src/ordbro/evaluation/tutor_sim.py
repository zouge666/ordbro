"""Simulated learners: does the adaptive policy use practice time better?

Each simulated learner has a hidden state per skill (known or not). Practice
on an unknown skill teaches it with a learner-specific probability, which is
lower when the prerequisites are not known yet. Answers follow the usual
slip and guess model. The tutor only sees the answers.

Three policies get the same learners and the same number of items:

* adaptive: the Ordbro policy (BKT, target success, skill graph);
* fixed: the skills in book order, four items each, then from the start;
* random: a random skill for every item.

This is a simulation with assumed numbers, not a study with people. It
shows how the policy behaves, not how much real learners would gain.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from ordbro.evaluation.metrics import mean
from ordbro.tutor import LearnerState, SkillGraph, TutorPolicy

GUESS = {"recognize": 1 / 3, "recall": 0.05, "produce": 0.05}


@dataclass
class SimLearner:
    group: str
    learn: float
    slip: float
    known: dict[str, bool]


def population(graph: SkillGraph, size: int, rng: random.Random) -> list[SimLearner]:
    learners = []
    for i in range(size):
        fast = i % 2 == 0
        returning = rng.random() < 0.3
        known = {
            s.id: returning and s.level == "A1" and not s.requires and rng.random() < 0.7
            for s in graph
        }
        learners.append(SimLearner("fast" if fast else "slow", 0.3 if fast else 0.12, 0.1, known))
    return learners


def simulate(graph: SkillGraph, size: int = 300, steps: int = 60, seed: int = 5) -> dict[str, Any]:
    base = population(graph, size, random.Random(seed))
    order = [s.id for s in graph]
    results: dict[str, Any] = {}
    for policy_name in ("adaptive", "fixed", "random"):
        rng = random.Random(f"{seed}-{policy_name}")
        per_learner = []
        for learner in base:
            known = dict(learner.known)
            start_known = sum(known.values())
            policy = TutorPolicy(graph)
            state = LearnerState("sim")
            wasted = 0
            reached = None
            for step in range(steps):
                if policy_name == "adaptive":
                    skill = policy.next_skill(state)
                    if skill is None:
                        break
                    skill_id = skill.id
                    mode = policy.mode_for(policy.mastery(state, skill_id))
                elif policy_name == "fixed":
                    skill_id = order[(step // 4) % len(order)]
                    mode = "recognize" if step % 4 < 2 else "recall"
                else:
                    skill_id = rng.choice(order)
                    mode = rng.choice(list(GUESS))
                if known[skill_id]:
                    wasted += 1
                    correct = rng.random() > learner.slip
                else:
                    correct = rng.random() < GUESS[mode]
                    ready = all(known[r] for r in graph.get(skill_id).requires)
                    if rng.random() < learner.learn * (1.0 if ready else 0.3):
                        known[skill_id] = True
                if policy_name == "adaptive":
                    policy.update(state, skill_id, correct, GUESS[mode])
                    state.record({"skill": skill_id, "correct": correct})
                if reached is None and sum(known.values()) >= 10:
                    reached = step + 1
            agreement = mean(
                [
                    float((policy.mastery(state, s.id) >= policy.mastered_at) == known[s.id])
                    for s in graph
                ]
            )
            per_learner.append(
                {
                    "group": learner.group,
                    "gained": sum(known.values()) - start_known,
                    "known": sum(known.values()),
                    "wasted": wasted / steps,
                    "reached_10": reached,
                    "agreement": agreement,
                }
            )
        results[policy_name] = _summary(per_learner, policy_name == "adaptive")
    return {"learners": size, "steps": steps, "skills": len(graph), "policies": results}


def _summary(rows: list[dict[str, Any]], with_agreement: bool) -> dict[str, Any]:
    def block(items: list[dict[str, Any]]) -> dict[str, Any]:
        reached = [r["reached_10"] for r in items if r["reached_10"] is not None]
        out = {
            "skills_known": round(mean([r["known"] for r in items]), 2),
            "skills_gained": round(mean([r["gained"] for r in items]), 2),
            "wasted_share": round(mean([r["wasted"] for r in items]), 3),
            "reached_10_share": round(len(reached) / len(items), 3),
            "steps_to_10": round(mean(reached), 1) if reached else None,
        }
        if with_agreement:
            out["estimate_agreement"] = round(mean([r["agreement"] for r in items]), 3)
        return out

    return {
        "all": block(rows),
        "fast": block([r for r in rows if r["group"] == "fast"]),
        "slow": block([r for r in rows if r["group"] == "slow"]),
    }
