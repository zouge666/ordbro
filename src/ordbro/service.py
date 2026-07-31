"""Wires content, retrieval, tutor, feedback and speech into one object."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from ordbro.config import Settings
from ordbro.content import load_content
from ordbro.exercises import Exercise, ExerciseEngine, generate_exercises, load_bank
from ordbro.feedback import FeedbackStore
from ordbro.grammar import GrammarChecker, apply_suggestions
from ordbro.llm import make_composer
from ordbro.nlp.tokenize import tokenize
from ordbro.rag import Answerer, KnowledgeBase
from ordbro.speech import assess
from ordbro.tutor import LearnerState, LearnerStore, SkillGraph, TutorPolicy
from ordbro.tutor.learner import utc_now


class Ordbro:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        data = settings.data_path
        self.content = load_content(data)
        self.graph = SkillGraph.load(data / "skills.json")
        self.policy = TutorPolicy(self.graph)
        self.kb = KnowledgeBase(
            self.content.documents,
            settings.rag.preset,
            glossary=self.content.glossary,
            rrf_k=settings.rag.rrf_k,
        )
        self.answerer = Answerer(
            self.kb, settings.rag.abstain_below, composer=make_composer(settings.llm)
        )
        self.exercises = load_bank(data / "exercises.json") + generate_exercises(
            self.content.lexicon
        )
        self.engine = ExerciseEngine(
            self.exercises, self.policy, self.content.lexicon, self.explain
        )
        self.checker = GrammarChecker(self.content.lexicon)
        self.sentences = json.loads((data / "speaking.json").read_text(encoding="utf-8"))
        self.learners = LearnerStore(settings.state_path / "learners")
        self.feedback = FeedbackStore(settings.state_path / "feedback.jsonl")
        self._lock = threading.Lock()

    @contextmanager
    def learner(self, learner_id: str):
        """Load a learner, let the caller change it, then save it."""
        with self._lock:
            state = self.learners.load(learner_id)
            yield state
            self.learners.save(state)

    # explanations from the course notes ---------------------------------------

    def explain(self, item: Exercise) -> dict[str, Any] | None:
        if not self.graph.has(item.skill):
            return None
        skill = self.graph.get(item.skill)
        query = " ".join(part for part in (item.explanation, item.text, skill.name_da) if part)
        result = self.kb.search(query, top_k=1, filters={"doc_id": list(skill.notes)})
        if not result.hits:
            return None
        return _source(result.hits[0].to_dict())

    def section(self, section_id: str) -> dict[str, Any] | None:
        doc_id = section_id.split("#", 1)[0]
        doc = self.content.document(doc_id)
        section = doc.section(section_id) if doc else None
        if not doc or not section:
            return None
        return {
            "doc_id": doc.id,
            "title": doc.title,
            "title_en": doc.metadata.get("title_en", ""),
            "heading": section.heading,
            "text": doc.section_text(section),
        }

    def note(self, doc_id: str) -> dict[str, Any] | None:
        doc = self.content.document(doc_id)
        if doc is None:
            return None
        return {
            "doc_id": doc.id,
            "title": doc.title,
            "title_en": doc.metadata.get("title_en", ""),
            "level": doc.metadata.get("level", ""),
            "summary_en": doc.metadata.get("summary_en", ""),
            "sections": [
                {"id": s.id, "heading": s.heading, "text": doc.section_text(s)}
                for s in doc.sections
            ],
        }

    # features -------------------------------------------------------------------

    def ask(self, question: str, top_k: int = 5) -> dict[str, Any]:
        answer = self.answerer.answer(question, top_k=top_k).to_dict()
        answer["word_cards"] = self.word_cards(question)
        return answer

    def word_cards(self, text: str, limit: int = 3) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        seen: set[str] = set()
        for token in tokenize(text):
            for entry, kind in self.content.lexicon.lookup(token):
                if entry.id in seen or entry.pos == "other" or len(token) < 2:
                    continue
                seen.add(entry.id)
                cards.append({**entry.to_dict(), "matched": token, "kind": kind})
        return cards[:limit]

    def check_text(self, text: str) -> dict[str, Any]:
        issues = self.checker.check(text)
        output = []
        for issue in issues:
            data = issue.to_dict()
            if self.graph.has(issue.skill):
                skill = self.graph.get(issue.skill)
                data["skill_name"] = skill.name
                data["note"] = skill.notes[0] if skill.notes else None
            output.append(data)
        return {
            "text": text,
            "issues": output,
            "corrected": apply_suggestions(text, issues),
        }

    def assess_speech(self, target: str, transcript: str) -> dict[str, Any]:
        result = assess(target, transcript).to_dict()
        for tip in result["tips"]:
            section = self.section(tip["section"])
            tip["note"] = section["text"] if section else ""
        return result

    def learner_summary(self, state: LearnerState, now: datetime | None = None) -> dict[str, Any]:
        now = now or utc_now()
        skills = []
        for skill in self.graph:
            p = self.policy.mastery(state, skill.id)
            counts = state.counts.get(skill.id, {"seen": 0, "correct": 0})
            unlocked = skill in self.graph.unlocked(
                state.mastery, self.policy.unlock_at, self.policy.params.p_init
            )
            skills.append(
                {
                    "id": skill.id,
                    "name": skill.name,
                    "name_da": skill.name_da,
                    "level": skill.level,
                    "about": skill.about,
                    "mastery": round(p, 3),
                    "mastered": p >= self.policy.mastered_at,
                    "unlocked": unlocked,
                    "requires": list(skill.requires),
                    "notes": list(skill.notes),
                    **counts,
                }
            )
        due = state.due_cards(now)
        return {
            "learner": state.learner_id,
            "skills": skills,
            "cards": {"total": len(state.cards), "due": len(due)},
            "upcoming": sorted((c.due for c in state.cards.values()), key=str)[:10],
            "history": state.history[-20:],
            "plan": self.policy.daily_plan(state, now),
        }

    def overview(self) -> dict[str, Any]:
        return {
            "knowledge_base": self.kb.stats(),
            "skills": len(self.graph),
            "exercises": len(self.exercises),
            "vocabulary": len(self.content.vocab),
            "sentences": len(self.sentences),
            "llm": self.settings.llm.provider,
        }


def _source(hit: dict[str, Any]) -> dict[str, Any]:
    keys = ("doc_id", "title", "title_en", "heading", "level", "text", "section_ids")
    return {key: hit.get(key) for key in keys}
