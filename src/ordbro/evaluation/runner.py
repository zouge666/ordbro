"""Run every study and write the results to eval/results."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ordbro.config import Settings
from ordbro.content import load_content
from ordbro.evaluation import grammar as grammar_eval
from ordbro.evaluation import retrieval as retrieval_eval
from ordbro.evaluation import speech as speech_eval
from ordbro.evaluation import tutor_sim
from ordbro.grammar import GrammarChecker
from ordbro.rag import KnowledgeBase
from ordbro.rag.presets import ABLATIONS, LADDER
from ordbro.rag.vectors import OllamaEmbedder
from ordbro.tutor import SkillGraph

STUDIES = ("retrieval", "grammar", "speech", "tutor")


def run_retrieval(settings: Settings, use_ollama: bool = True) -> dict[str, Any]:
    content = load_content(settings.data_path)
    test = retrieval_eval.load_questions(settings.root / "eval" / "retrieval_test.jsonl")
    dev = retrieval_eval.load_questions(settings.root / "eval" / "retrieval_dev.jsonl")
    ollama_ok = use_ollama and OllamaEmbedder().available()
    presets, by_type, failures, skipped = [], {}, {}, []
    for preset in LADDER + ABLATIONS:
        if preset.needs_ollama and not ollama_ok:
            skipped.append(preset.name)
            continue
        kb = KnowledgeBase(content.documents, preset, glossary=content.glossary)
        rows = retrieval_eval.run(kb, test)
        sizes = [chunk.end - chunk.start for chunk in kb.chunks]
        presets.append(
            {
                "name": preset.name,
                "label": preset.label,
                "group": "ladder" if preset in LADDER else "ablation",
                "chunks": len(kb.chunks),
                "mean_chunk_chars": round(sum(sizes) / len(sizes)),
                **retrieval_eval.aggregate(rows),
            }
        )
        if preset.name in {"c0", "c1n", "c6"}:
            by_type[preset.name] = retrieval_eval.by_type(rows)
            failures[preset.name] = retrieval_eval.failures(rows, kb)

    abstention = {}
    for field in ("text", "index_text"):
        kb = KnowledgeBase(
            content.documents, "ordbro", glossary=content.glossary, confidence_on=field
        )
        tuned = retrieval_eval.tune_threshold(retrieval_eval.run(kb, dev))
        abstention[field] = {
            **tuned,
            **retrieval_eval.abstention(retrieval_eval.run(kb, test), tuned["threshold"]),
        }
    counts: dict[str, int] = {}
    for q in test:
        counts[q.type] = counts.get(q.type, 0) + 1
    return {
        "test_questions": len(test),
        "dev_questions": len(dev),
        "types": counts,
        "presets": presets,
        "skipped": skipped,
        "by_type": by_type,
        "failures": failures,
        "abstention": abstention,
    }


def run_grammar(settings: Settings) -> dict[str, Any]:
    content = load_content(settings.data_path)
    items = grammar_eval.load_items(settings.root / "eval" / "grammar_test.jsonl")
    return grammar_eval.run(GrammarChecker(content.lexicon), items)


def run_speech(settings: Settings) -> dict[str, Any]:
    content = load_content(settings.data_path)
    sentences = json.loads((settings.data_path / "speaking.json").read_text(encoding="utf-8"))
    vocabulary = sorted({e.da for e in content.vocab if " " not in e.da})
    return speech_eval.simulate([s["text"] for s in sentences], vocabulary)


def run_tutor(settings: Settings) -> dict[str, Any]:
    graph = SkillGraph.load(settings.data_path / "skills.json")
    return tutor_sim.simulate(graph)


def run_all(settings: Settings, studies=STUDIES, out_dir: Path | None = None, use_ollama=True):
    out = out_dir or settings.root / "eval" / "results"
    out.mkdir(parents=True, exist_ok=True)
    runners = {
        "retrieval": lambda: run_retrieval(settings, use_ollama),
        "grammar": lambda: run_grammar(settings),
        "speech": lambda: run_speech(settings),
        "tutor": lambda: run_tutor(settings),
    }
    results = {}
    for name in studies:
        data = runners[name]()
        data["created"] = datetime.now(UTC).isoformat(timespec="seconds")
        (out / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        results[name] = data
    return results
