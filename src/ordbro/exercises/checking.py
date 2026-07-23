"""Answer checking that is strict about grammar but kind about typing.

* Case, extra spaces and punctuation do not matter.
* "ae", "oe" and "aa" are accepted for æ, ø and å, with a friendly note.
  Many learners do not have a Danish keyboard.
* One wrong letter in a longer word is "almost", unless the answer is
  another real word form. "huse" for "huset" is a grammar mistake, not a
  typo.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ordbro.nlp.distance import levenshtein

_PUNCT = re.compile(r"[.,!?;:\"“”«»()]")
_SPACE = re.compile(r"\s+")
_FOLD = str.maketrans({"æ": "ae", "ø": "oe", "å": "aa"})


@dataclass(frozen=True)
class Verdict:
    correct: bool
    matched: str | None = None
    note: str = ""
    close: bool = False


def normalize(text: str) -> str:
    text = text.replace("’", "'").lower()
    return _SPACE.sub(" ", _PUNCT.sub(" ", text)).strip()


def fold(text: str) -> str:
    return normalize(text).translate(_FOLD)


def check_answer(
    answer: str,
    accepted: Sequence[str],
    is_known_word: Callable[[str], bool] | None = None,
) -> Verdict:
    given = normalize(answer)
    if not given:
        return Verdict(False)
    for option in accepted:
        if given == normalize(option):
            return Verdict(True, option)
    for option in accepted:
        if fold(given) == fold(option):
            return Verdict(
                True,
                option,
                note=f"Right. With Danish letters it is written: {option}",
            )
    for option in accepted:
        target = normalize(option)
        if len(target) >= 4 and levenshtein(given, target) == 1:
            if is_known_word and " " not in given and is_known_word(given):
                continue
            return Verdict(False, option, close=True)
    return Verdict(False)
