"""Word forms from the vocabulary list.

The lexicon is the single source of truth for gender, definite forms,
plurals and verb forms. Exercises and the grammar checker both use it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

_NOUN_FORMS = ("da", "definite", "plural", "plural_definite")
_VERB_FORMS = ("da", "present", "past", "perfect")
_ADJ_FORMS = ("da", "t_form", "plural", "definite", "comparative", "superlative")


@dataclass(frozen=True)
class VocabEntry:
    da: str
    en: str
    pos: str
    level: str = "A1"
    topic: str = ""
    gender: str | None = None
    definite: str | None = None
    plural: str | None = None
    plural_definite: str | None = None
    present: str | None = None
    past: str | None = None
    perfect: str | None = None
    aux: str | None = None
    group: str | None = None
    t_form: str | None = None
    comparative: str | None = None
    superlative: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VocabEntry:
        allowed = {f.name for f in fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown vocabulary fields for '{data.get('da')}': {sorted(unknown)}")
        return cls(**data)

    @property
    def id(self) -> str:
        return f"{self.pos}:{self.da}"

    def forms(self) -> dict[str, str]:
        names = {"noun": _NOUN_FORMS, "verb": _VERB_FORMS, "adj": _ADJ_FORMS}.get(self.pos, ("da",))
        return {name: getattr(self, name) for name in names if getattr(self, name)}

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


class Lexicon:
    def __init__(self, entries: list[VocabEntry]) -> None:
        self.entries = entries
        self._forms: dict[str, list[tuple[VocabEntry, str]]] = {}
        self._base: dict[str, list[VocabEntry]] = {}
        for entry in entries:
            self._base.setdefault(entry.da.lower(), []).append(entry)
            for kind, form in entry.forms().items():
                self._forms.setdefault(form.lower(), []).append((entry, kind))
        self._wrong_past = self._build_wrong_past()

    def lookup(self, form: str) -> list[tuple[VocabEntry, str]]:
        return self._forms.get(form.lower(), [])

    def find(self, form: str, pos: str, kinds: tuple[str, ...] | None = None):
        for entry, kind in self.lookup(form):
            if entry.pos == pos and (kinds is None or kind in kinds):
                return entry, kind
        return None

    def noun(self, form: str, kinds: tuple[str, ...] | None = None):
        return self.find(form, "noun", kinds)

    def verb(self, form: str, kinds: tuple[str, ...] | None = None):
        return self.find(form, "verb", kinds)

    def adjective(self, form: str, kinds: tuple[str, ...] | None = None):
        return self.find(form, "adj", kinds)

    def word(self, base: str, pos: str | None = None) -> VocabEntry | None:
        for entry in self._base.get(base.lower(), []):
            if pos is None or entry.pos == pos:
                return entry
        return None

    def by_pos(self, pos: str) -> list[VocabEntry]:
        return [entry for entry in self.entries if entry.pos == pos]

    def is_known(self, form: str) -> bool:
        return form.lower() in self._forms

    def wrong_past(self, form: str) -> str | None:
        """Return the right past tense for an over-regular form like "gåede"."""
        return self._wrong_past.get(form.lower())

    def _build_wrong_past(self) -> dict[str, str]:
        wrong: dict[str, str] = {}
        for entry in self.by_pos("verb"):
            if entry.group == "modal" or not entry.past:
                continue
            stem = entry.da[:-1] if entry.da.endswith("e") and len(entry.da) > 2 else entry.da
            for candidate in (stem + "ede", stem + "te", entry.da + "de"):
                if candidate != entry.past and candidate not in self._forms:
                    wrong.setdefault(candidate, entry.past)
        return wrong
