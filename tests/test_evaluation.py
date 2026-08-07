import pytest

from ordbro.config import load_settings
from ordbro.content import load_content
from ordbro.evaluation import grammar as grammar_eval
from ordbro.evaluation import retrieval as retrieval_eval
from ordbro.evaluation import speech as speech_eval
from ordbro.evaluation import tutor_sim
from ordbro.evaluation.metrics import hit_at_k, ndcg_at_k, reciprocal_rank
from ordbro.grammar import GrammarChecker
from ordbro.rag import KnowledgeBase
from ordbro.tutor import SkillGraph

SETTINGS = load_settings()


def test_ranking_metrics():
    rel = [False, True, False, True]
    assert hit_at_k(rel, 1) == 0.0 and hit_at_k(rel, 2) == 1.0
    assert reciprocal_rank(rel) == 0.5
    assert reciprocal_rank([False, False]) == 0.0
    assert ndcg_at_k([True, False], 5, 1) == 1.0
    assert 0 < ndcg_at_k(rel, 5, 2) < 1


def test_question_sets_reference_existing_sections():
    content = load_content(SETTINGS.data_path)
    known = {s.id for d in content.documents for s in d.sections}
    for name in ("retrieval_test.jsonl", "retrieval_dev.jsonl"):
        questions = retrieval_eval.load_questions(SETTINGS.root / "eval" / name)
        assert questions
        for q in questions:
            assert set(q.gold) <= known, q.question


def test_retrieval_run_and_threshold(mini_docs, mini_glossary):
    kb = KnowledgeBase(mini_docs, "ordbro", glossary=mini_glossary)
    questions = [
        retrieval_eval.Question(
            "1", "rule-en", "irregular past tense", ("datid#uregelmæssige-verber",)
        ),
        retrieval_eval.Question("2", "unanswerable", "photosynthesis in leaves", ()),
    ]
    rows = retrieval_eval.run(kb, questions, top_k=3)
    assert rows[0]["rank"] == 1 and rows[0]["precision1"] > 0.5
    assert retrieval_eval.aggregate(rows)["recall@1"] == 1.0
    tuned = retrieval_eval.tune_threshold(rows)
    assert tuned["dev_accuracy"] == 1.0
    assert retrieval_eval.abstention(rows, tuned["threshold"])["unanswerable_abstained"] == 1.0


def test_grammar_evaluation_counts():
    checker = GrammarChecker(load_content(SETTINGS.data_path).lexicon)
    items = [
        {
            "id": "1",
            "text": "Jeg har en Kat.",
            "errors": [{"rule": "capital-noun", "wrong": "Kat", "fix": "kat"}],
        },
        {"id": "2", "text": "Jeg har en kat.", "errors": []},
    ]
    result = grammar_eval.run(checker, items)
    assert result["detection_recall"] == 1.0 and result["false_alarm_rate"] == 0.0
    assert result["fix_accuracy"] == 1.0


def test_speech_simulation_is_deterministic_and_n_best_helps():
    vocab = ["hus", "bil", "kat", "mad", "dag", "pige", "skole", "tog"]
    sentences = ["Jeg hedder Anna.", "Hvad hedder du?", "Vi spiser mad i dag."]
    a = speech_eval.simulate(sentences, vocab, rates=(0.2,), lm_fix=(0.0,), trials=20)
    b = speech_eval.simulate(sentences, vocab, rates=(0.2,), lm_fix=(0.0,), trials=20)
    assert a == b
    one, three = a["rows"]
    assert three["false_flags_per_word"] < one["false_flags_per_word"]


def test_tutor_simulation_shape():
    graph = SkillGraph.load(SETTINGS.data_path / "skills.json")
    result = tutor_sim.simulate(graph, size=10, steps=15, seed=1)
    assert set(result["policies"]) == {"adaptive", "fixed", "random"}
    for data in result["policies"].values():
        assert 0 <= data["all"]["skills_known"] <= len(graph)
        assert 0 <= data["all"]["wasted_share"] <= 1


@pytest.mark.parametrize("study", ["grammar", "speech", "tutor"])
def test_saved_results_exist(study):
    assert (SETTINGS.root / "eval" / "results" / f"{study}.json").exists()
