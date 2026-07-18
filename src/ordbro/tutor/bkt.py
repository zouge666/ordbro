"""Bayesian Knowledge Tracing (Corbett and Anderson, 1994).

Each skill has a probability that the learner knows it. After every answer
the probability is updated with Bayes' rule, and then there is a chance
that the learner learned the skill from the practice itself.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BKTParams:
    p_init: float = 0.15
    p_learn: float = 0.2
    p_slip: float = 0.1
    p_guess: float = 0.2


def predict_correct(p_known: float, params: BKTParams, guess: float | None = None) -> float:
    g = params.p_guess if guess is None else guess
    return p_known * (1 - params.p_slip) + (1 - p_known) * g


def update_mastery(
    p_known: float,
    correct: bool,
    params: BKTParams,
    guess: float | None = None,
) -> float:
    g = params.p_guess if guess is None else guess
    slip = params.p_slip
    if correct:
        evidence = p_known * (1 - slip)
        posterior = evidence / (evidence + (1 - p_known) * g)
    else:
        evidence = p_known * slip
        posterior = evidence / (evidence + (1 - p_known) * (1 - g))
    return posterior + (1 - posterior) * params.p_learn
