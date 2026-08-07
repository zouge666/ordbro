"""Retrieval evaluation over the preset ladder.

A retrieved chunk is relevant when it overlaps one of the gold sections of
the question. This works for both chunkers: a recursive chunk that covers
two sections is relevant for both.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ordbro.evaluation.metrics import first_relevant, hit_at_k, mean, ndcg_at_k, reciprocal_rank
from ordbro.rag import KnowledgeBase
from ordbro.rag.chunking import Chunk

KS = (1, 3, 5)


@dataclass(frozen=True)
class Question:
    id: str
    type: str
    question: str
    gold: tuple[str, ...]

    @property
    def answerable(self) -> bool:
        return bool(self.gold)


def load_questions(path: Path) -> list[Question]:
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    return [Question(r["id"], r["type"], r["question"], tuple(r["gold"])) for r in rows]


def is_relevant(chunk: Chunk, gold: Sequence[str]) -> bool:
    return any(section in gold for section in chunk.section_ids)


def run(kb: KnowledgeBase, questions: Sequence[Question], top_k: int = 10) -> list[dict[str, Any]]:
    rows = []
    for q in questions:
        result = kb.search(q.question, top_k=top_k)
        relevance = [is_relevant(hit.chunk, q.gold) for hit in result.hits]
        gold_docs = {g.split("#", 1)[0] for g in q.gold}
        top = result.hits[0].chunk if result.hits else None
        rows.append(
            {
                "id": q.id,
                "type": q.type,
                "question": q.question,
                "answerable": q.answerable,
                "gold": list(q.gold),
                "rank": first_relevant(relevance),
                "relevance": relevance,
                "total_relevant": sum(1 for c in kb.chunks if is_relevant(c, q.gold)),
                "note_hit1": bool(top and top.doc_id in gold_docs),
                "top": [hit.chunk.id for hit in result.hits[:3]],
                "precision1": round(text_precision(kb, top.id, q.gold), 4)
                if top and q.gold
                else 0.0,
                "top_section": list(top.section_ids) if top else [],
                "confidence": round(result.confidence, 4),
                "expansions": result.expansions,
            }
        )
    return rows


def text_precision(kb: KnowledgeBase, chunk_id: str, gold: Sequence[str]) -> float:
    """Share of the shown passage that lies inside the gold sections."""
    chunk = kb.chunk(chunk_id)
    doc = kb.documents[chunk.doc_id]
    inside = 0
    for section in doc.sections:
        if section.id in gold:
            inside += max(0, min(chunk.end, section.end) - max(chunk.start, section.start))
    return inside / max(1, chunk.end - chunk.start)


def aggregate(rows: Sequence[dict[str, Any]]) -> dict[str, float]:
    answerable = [r for r in rows if r["answerable"]]
    out = {f"recall@{k}": mean([hit_at_k(r["relevance"], k) for r in answerable]) for k in KS}
    out["mrr"] = mean([reciprocal_rank(r["relevance"]) for r in answerable])
    out["ndcg@5"] = mean([ndcg_at_k(r["relevance"], 5, r["total_relevant"]) for r in answerable])
    out["note@1"] = mean([float(r["note_hit1"]) for r in answerable])
    out["precision@1"] = mean([r["precision1"] for r in answerable])
    out["n"] = len(answerable)
    return {
        key: round(value, 4) if isinstance(value, float) else value for key, value in out.items()
    }


def by_type(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, float]]:
    types = sorted({r["type"] for r in rows if r["answerable"]})
    return {t: aggregate([r for r in rows if r["type"] == t]) for t in types}


def tune_threshold(rows: Sequence[dict[str, Any]], step: float = 0.005) -> dict[str, float]:
    """Pick the abstention threshold with the best accuracy on the dev rows."""
    best: list[tuple[float, float]] = []
    t = 0.0
    while t <= 0.6 + 1e-9:
        correct = sum(1 for r in rows if (r["confidence"] >= t) == r["answerable"])
        best.append((correct / len(rows), round(t, 4)))
        t += step
    top = max(acc for acc, _ in best)
    tied = [thr for acc, thr in best if acc == top]
    return {"threshold": tied[len(tied) // 2], "dev_accuracy": round(top, 4)}


def abstention(rows: Sequence[dict[str, Any]], threshold: float) -> dict[str, Any]:
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    answered = [r for r in answerable if r["confidence"] >= threshold]
    return {
        "threshold": threshold,
        "unanswerable_abstained": round(
            mean([float(r["confidence"] < threshold) for r in unanswerable]), 4
        ),
        "answerable_answered": round(len(answered) / len(answerable), 4) if answerable else 0.0,
        "answered_and_right_at_1": round(
            sum(1 for r in answered if r["rank"] == 1) / len(answerable), 4
        )
        if answerable
        else 0.0,
        "false_answers": [r["question"] for r in unanswerable if r["confidence"] >= threshold],
        "false_abstentions": [r["question"] for r in answerable if r["confidence"] < threshold],
    }


def failures(rows: Sequence[dict[str, Any]], kb: KnowledgeBase, limit: int = 12) -> list[dict]:
    out = []
    for r in rows:
        if not r["answerable"] or r["rank"] == 1:
            continue
        top = kb.chunk(r["top"][0]) if r["top"] else None
        out.append(
            {
                "question": r["question"],
                "type": r["type"],
                "rank": r["rank"],
                "gold": r["gold"],
                "got": list(top.section_ids) if top else [],
                "right_note": r["note_hit1"],
            }
        )
    return out[:limit]
