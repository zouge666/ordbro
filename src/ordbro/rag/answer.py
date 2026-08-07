"""Answers built from retrieved passages, with no language model needed.

The answer is extractive: it shows the most relevant lines of the best
passage and says where they come from. When the evidence is weak, the
assistant says that it does not know instead of guessing.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ordbro.rag.knowledge_base import Hit, KnowledgeBase

Composer = Callable[[str, Sequence[Hit]], str]


@dataclass
class Answer:
    question: str
    abstained: bool
    confidence: float
    lines: list[str] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    summary_en: str = ""
    text: str = ""
    mode: str = "extractive"
    hits: list[Hit] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)
    expansions: list[str] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "abstained": self.abstained,
            "confidence": round(self.confidence, 4),
            "lines": self.lines,
            "source": self.source,
            "summary_en": self.summary_en,
            "text": self.text,
            "mode": self.mode,
            "terms": self.terms,
            "expansions": self.expansions,
            "passages": [hit.to_dict() for hit in self.hits],
            "trace": self.trace,
        }


class Answerer:
    def __init__(
        self,
        kb: KnowledgeBase,
        abstain_below: float = 0.095,
        max_lines: int = 3,
        composer: Composer | None = None,
    ) -> None:
        self.kb = kb
        self.abstain_below = abstain_below
        self.max_lines = max_lines
        self.composer = composer

    def answer(
        self,
        question: str,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> Answer:
        result = self.kb.search(question, top_k=top_k, filters=filters)
        answer = Answer(
            question=question,
            abstained=not result.hits or result.confidence < self.abstain_below,
            confidence=result.confidence,
            hits=result.hits,
            terms=result.terms,
            expansions=result.expansions,
            trace=result.trace,
        )
        if answer.abstained:
            return answer
        best = result.hits[0]
        doc = self.kb.documents[best.chunk.doc_id]
        answer.lines = self.best_lines(best.chunk.text, result.terms)
        answer.summary_en = str(doc.metadata.get("summary_en", ""))
        answer.source = {
            "doc_id": doc.id,
            "title": doc.title,
            "title_en": doc.metadata.get("title_en", ""),
            "heading": best.chunk.heading,
            "level": doc.metadata.get("level", ""),
            "section_ids": list(best.chunk.section_ids),
        }
        answer.text = "\n".join(answer.lines)
        if self.composer is not None:
            try:
                answer.text = self.composer(question, result.hits[:3])
                answer.mode = "llm"
            except Exception as exc:  # the extractive answer is still there
                answer.trace.setdefault("warnings", []).append(f"composer failed: {exc}")
        return answer

    def best_lines(self, text: str, terms: Sequence[str]) -> list[str]:
        lines = [
            line.strip().lstrip("-* ").strip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not lines:
            return []
        wanted = set(terms)
        scored = []
        for index, line in enumerate(lines):
            line_terms = self.kb.analyzer.index_terms(line)
            overlap = len(wanted.intersection(line_terms))
            scored.append((overlap / math.sqrt(len(line_terms) + 1), -index, index))
        if max(item[0] for item in scored) == 0:
            return lines[: self.max_lines]
        chosen = sorted(scored, reverse=True)[: self.max_lines]
        return [lines[index] for _, _, index in sorted(chosen, key=lambda item: item[2])]
