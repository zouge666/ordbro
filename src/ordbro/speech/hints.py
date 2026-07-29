"""Pronunciation hints for Danish spelling patterns.

The rules look at spelling only. They can tell a learner which sound in a
word is often hard, but they cannot hear the learner. Each hint links to a
section of the pronunciation note.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_VOWEL = "aeiouyæøå"


@dataclass(frozen=True)
class Hint:
    id: str
    title: str
    tip: str
    examples: str
    section: str
    pattern: re.Pattern[str]

    def to_dict(self) -> dict[str, str]:
        data = asdict(self)
        data.pop("pattern")
        return data


HINTS: tuple[Hint, ...] = (
    Hint(
        "silent-h",
        "Silent h in hv-",
        "Do not say the h. Start with the v sound.",
        "hvad, hvor, hvem",
        "a1-udtale#stumt-h-i-hv",
        re.compile(r"^hv"),
    ),
    Hint(
        "silent-d",
        "Silent d after n and l",
        "The d after n or l is usually not said.",
        "hund, mand, kold",
        "a1-udtale#stumt-d",
        re.compile(r"[nl]d(?:[est]|e[rt]|en)?$|[nl]dt"),
    ),
    Hint(
        "soft-d",
        "Soft d",
        "After a vowel the d is soft, close to th in the English word 'the'.",
        "mad, gade, hedder",
        "a1-udtale#blødt-d",
        re.compile(rf"[{_VOWEL}]d(?:d|$|[{_VOWEL}]|e[rnt]|et$)"),
    ),
    Hint(
        "soft-g",
        "Soft or silent g",
        "After a vowel the g is soft or not said at all. -ig sounds like 'i'.",
        "pige, dag, dejlig",
        "a1-udtale#blødt-g",
        re.compile(rf"[{_VOWEL}]g(?:$|e)"),
    ),
    Hint(
        "vowel-r",
        "The r after a vowel",
        "After a vowel the r is almost a vowel. Do not roll it.",
        "mor, far, her",
        "a1-udtale#r-lyden",
        re.compile(rf"[{_VOWEL}]r"),
    ),
    Hint(
        "stød",
        "The stød",
        "Make a small break in your voice. It can change the meaning: hun and hund.",
        "hund, mand",
        "a1-udtale#stød",
        re.compile(r"^(hund|mand|manden|hunden)$"),
    ),
    Hint(
        "vowels",
        "æ, ø, å and y",
        "These vowels do not exist in English. Listen to the model and copy the mouth shape.",
        "æble, rød, på, syv",
        "a1-udtale#vokalerne-æ-ø-å-og-y",
        re.compile(r"[æøåy]"),
    ),
)


def hints_for(word: str) -> list[Hint]:
    word = word.lower()
    found = [hint for hint in HINTS if hint.pattern.search(word)]
    if any(h.id == "silent-d" for h in found):
        found = [h for h in found if h.id != "soft-d"]
    return found
