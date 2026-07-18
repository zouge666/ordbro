from datetime import UTC, datetime, timedelta

import pytest

from ordbro.config import load_settings
from ordbro.tutor import (
    BKTParams,
    Card,
    LearnerState,
    LearnerStore,
    Skill,
    SkillGraph,
    TutorPolicy,
    grade_from_outcome,
    predict_correct,
    review,
    update_mastery,
)

NOW = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)


def graph():
    return SkillGraph(
        [
            Skill("a", "A", "A", "A1"),
            Skill("b", "B", "B", "A1"),
            Skill("c", "C", "C", "A2", requires=("a",)),
        ]
    )


def test_bkt_moves_up_after_correct_and_down_after_wrong():
    params = BKTParams()
    up = update_mastery(0.5, True, params)
    down = update_mastery(0.5, False, params)
    assert up > 0.5 > down
    p = params.p_init
    for _ in range(8):
        p = update_mastery(p, True, params)
    assert p > 0.95


def test_easy_guessing_gives_less_evidence():
    params = BKTParams()
    assert update_mastery(0.3, True, params, guess=0.5) < update_mastery(
        0.3, True, params, guess=0.05
    )


def test_predict_correct_is_between_guess_and_one_minus_slip():
    params = BKTParams()
    assert predict_correct(0.0, params) == pytest.approx(params.p_guess)
    assert predict_correct(1.0, params) == pytest.approx(1 - params.p_slip)


def test_sm2_intervals_grow_and_failure_resets():
    card = Card.new("noun:bil", NOW)
    card = review(card, 5, NOW)
    assert card.interval == 1.0
    card = review(card, 5, NOW)
    assert card.interval == 6.0
    card = review(card, 4, NOW)
    assert card.interval > 6.0
    failed = review(card, 1, NOW)
    assert failed.reps == 0 and failed.lapses == 1
    assert datetime.fromisoformat(failed.due) == NOW + timedelta(minutes=10)
    assert failed.ease >= 1.3


def test_grades():
    assert grade_from_outcome(True, 1) == 5
    assert grade_from_outcome(True, 2) == 3
    assert grade_from_outcome(False, 1) == 1


def test_skill_graph_rejects_unknown_and_cyclic_prerequisites():
    with pytest.raises(ValueError):
        SkillGraph([Skill("a", "A", "A", "A1", requires=("x",))])
    with pytest.raises(ValueError):
        SkillGraph(
            [
                Skill("a", "A", "A", "A1", requires=("b",)),
                Skill("b", "B", "B", "A1", requires=("a",)),
            ]
        )


def test_real_skill_graph_loads():
    skills = SkillGraph.load(load_settings().data_path / "skills.json")
    assert len(skills) == 18
    assert skills.get("negation").requires == ("word_order",)


def test_policy_starts_in_graph_order_and_keeps_locked_skills_closed():
    policy = TutorPolicy(graph())
    state = LearnerState("t")
    assert policy.next_skill(state).id == "a"
    assert "c" not in {s.id for s in policy.open_skills(state)}
    state.mastery["a"] = 0.7
    assert "c" in {s.id for s in policy.open_skills(state)}


def test_policy_prefers_the_skill_closest_to_target_success():
    policy = TutorPolicy(graph())
    state = LearnerState("t", mastery={"a": 0.15, "b": 0.6})
    assert policy.next_skill(state).id == "b"


def test_policy_skips_mastered_skills_and_avoids_long_repeats():
    policy = TutorPolicy(graph())
    state = LearnerState("t", mastery={"a": 0.99})
    assert policy.next_skill(state).id == "b"
    state = LearnerState("t", mastery={"b": 0.6})
    for _ in range(3):
        state.record({"skill": "b", "correct": True})
    assert policy.next_skill(state).id != "b"


def test_modes_follow_mastery():
    policy = TutorPolicy(graph())
    assert [policy.mode_for(p) for p in (0.1, 0.5, 0.9)] == ["recognize", "recall", "produce"]


def test_daily_plan_lists_focus_skills_and_due_cards():
    policy = TutorPolicy(graph())
    state = LearnerState("t")
    state.cards["noun:bil"] = Card.new("noun:bil", NOW - timedelta(hours=1))
    plan = policy.daily_plan(state, NOW)
    assert plan["due_reviews"] == 1
    assert [f["id"] for f in plan["focus"]] == ["a", "b"]


def test_store_round_trip_and_id_check(tmp_path):
    store = LearnerStore(tmp_path)
    state = store.load("anna")
    state.mastery["a"] = 0.4
    state.cards["noun:bil"] = Card.new("noun:bil", NOW)
    state.record({"skill": "a", "correct": True})
    store.save(state)
    loaded = store.load("anna")
    assert loaded.mastery == {"a": 0.4}
    assert loaded.cards["noun:bil"].item_id == "noun:bil"
    assert loaded.counts == {"a": {"seen": 1, "correct": 1}}
    with pytest.raises(ValueError):
        store.path("../evil")
    assert store.reset("anna").mastery == {}
