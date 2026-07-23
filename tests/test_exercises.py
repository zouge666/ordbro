from datetime import UTC, datetime

import pytest

from ordbro.config import load_settings
from ordbro.content import load_content
from ordbro.exercises import ExerciseEngine, check_answer, generate_exercises, load_bank
from ordbro.tutor import LearnerState, SkillGraph, TutorPolicy

NOW = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def setup():
    settings = load_settings()
    content = load_content(settings.data_path)
    bank = load_bank(settings.data_path / "exercises.json")
    generated = generate_exercises(content.lexicon)
    graph = SkillGraph.load(settings.data_path / "skills.json")
    return content, bank, generated, graph


def engine(setup, explainer=None):
    content, bank, generated, graph = setup
    return ExerciseEngine(bank + generated, TutorPolicy(graph), content.lexicon, explainer, seed=1)


def test_bank_and_generated_items_are_valid(setup):
    _, bank, generated, graph = setup
    assert len(bank) >= 80
    ids = [item.id for item in bank + generated]
    assert len(ids) == len(set(ids))
    for item in bank + generated:
        assert all(answer.strip() for answer in item.answers), item.id
        assert not item.skill or graph.has(item.skill), item.id
    assert all(
        graph.has(skill.id) and any(i.skill == skill.id for i in bank + generated)
        for skill in graph
    )


def test_generated_adjective_follows_noun_gender(setup):
    _, _, generated, _ = setup
    items = {item.id: item for item in generated}
    assert items["gen:adj:stor:hus:sg"].answers == ("stort",)
    assert items["gen:adj:stor:bil:sg"].answers == ("stor",)
    assert items["gen:adj:stor:bil:pl"].answers == ("store",)
    assert items["gen:past:gå"].answers == ("gik",)


def test_answer_checking_rules(setup):
    content = setup[0]
    assert check_answer(" Jeg hedder Ali. ", ["Jeg hedder Ali"]).correct
    folded = check_answer("gaar", ["går"])
    assert folded.correct and "går" in folded.note
    assert check_answer("bilem", ["bilen"]).close
    known = content.lexicon.is_known
    assert not check_answer("huse", ["huset"], known).close
    assert not check_answer("", ["huset"]).correct


def test_public_view_hides_answers(setup):
    item = setup[1][0]
    public = item.public()
    assert "answers" not in public and "hint" not in public
    assert public["mode"] == "recognize"


def test_two_step_feedback(setup):
    eng = engine(setup)
    state = LearnerState("t")
    first = eng.answer(state, "past-01", "gåede", 1, NOW)
    assert not first.correct and not first.final and first.hint and not first.answer
    other = engine(setup).answer(LearnerState("u"), "past-01", "gik", 1, NOW)
    assert first.mastery_after < other.mastery_after
    second = eng.answer(state, "past-01", "gåede", 2, NOW)
    assert second.final and second.answer == "gik"
    assert second.mastery_after is None
    assert state.counts["past_tense"] == {"seen": 1, "correct": 0}


def test_correct_answer_raises_mastery_and_asks_for_a_source(setup):
    calls = []
    eng = engine(setup, explainer=lambda item: calls.append(item.id) or {"doc_id": "x"})
    state = LearnerState("t")
    fb = eng.answer(state, "order-01", "i dag går jeg i skole", 1, NOW)
    assert fb.correct and fb.final
    assert fb.mastery_after > fb.mastery_before
    assert fb.source == {"doc_id": "x"} and calls == ["order-01"]


def test_flashcards_update_the_review_card(setup):
    eng = engine(setup)
    state = LearnerState("t")
    item = eng.next_review(state, NOW)
    assert item.type == "flashcard"
    eng.answer(state, item.id, item.answers[0], 1, NOW)
    assert state.cards[item.card_id].reps == 1


def test_next_follows_policy_mode(setup):
    eng = engine(setup)
    state = LearnerState("t")
    item, reason = eng.next(state, NOW)
    assert reason == "adaptive" and item.skill == "greetings" and item.mode == "recognize"
    item, reason = eng.next(state, NOW, focus="negation")
    assert item.skill == "negation" and reason == "chosen skill"
