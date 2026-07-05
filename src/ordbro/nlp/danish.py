"""Danish word lists, a Snowball stemmer and a compound splitter."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable

DANISH_STOPWORDS = frozenset(
    """
    ad af alle alt anden at blev blive bliver da de dem den denne der deres det dette dig
    din dine disse dog du efter eller en end er et for fra ham han hans har havde have hende
    hendes her hos hun hvad hvis hvor i ikke ind jeg jer jo kunne man mange med meget men
    mig min mine mit mod ned noget nogle nu når og også om op os over på selv sig sin sine
    sit skal skulle som sådan thi til ud under var vi vil ville vor været
    """.split()
)

ENGLISH_STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are as at be because been before
    being below between both but by can could did do does doing down during each few for
    from further had has have having he her here hers him his how i if in into is it its
    just me more most my no nor not now of off on once only or other our out over own same
    she should so some such than that the their them then there these they this those
    through to too under until up very was we were what when where which while who whom
    why will with would you your
    """.split()
)

_VOWELS = frozenset("aeiouyæåø")
_S_ENDINGS = frozenset("abcdfghjklmnoprtvyzå")
_STEP1 = sorted(
    """
    hed ethed ered e erede ende erende ene erne ere en heden eren er heder erer heds es
    endes erendes enes ernes eres ens hedens erens ers ets erets et eret s
    """.split(),
    key=len,
    reverse=True,
)
_STEP2 = ("gd", "dt", "gt", "kt")
_STEP3 = ("elig", "løst", "lig", "els", "ig")


class DanishStemmer:
    """The Snowball stemming algorithm for Danish.

    See https://snowballstem.org/algorithms/danish/stemmer.html. The steps
    below follow that description; R1 is computed once on the input word.
    """

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def stem(self, word: str) -> str:
        word = word.lower()
        cached = self._cache.get(word)
        if cached is not None:
            return cached
        result = self._stem(word)
        if len(self._cache) < 50_000:
            self._cache[word] = result
        return result

    def _stem(self, word: str) -> str:
        if len(word) < 3:
            return word
        r1 = _r1(word)
        word = _main_suffix(word, r1)
        word = _consonant_pair(word, r1)
        word = _other_suffix(word, r1)
        return _undouble(word, r1)


def _r1(word: str) -> int:
    for i in range(1, len(word)):
        if word[i] not in _VOWELS and word[i - 1] in _VOWELS:
            return max(i + 1, 3)
    return len(word)


def _main_suffix(word: str, r1: int) -> str:
    for suffix in _STEP1:
        if word.endswith(suffix) and len(word) - len(suffix) >= r1:
            if suffix == "s":
                if len(word) >= 2 and word[-2] in _S_ENDINGS:
                    return word[:-1]
                return word
            return word[: -len(suffix)]
    return word


def _consonant_pair(word: str, r1: int) -> str:
    for pair in _STEP2:
        if word.endswith(pair) and len(word) - 2 >= r1:
            return word[:-1]
    return word


def _other_suffix(word: str, r1: int) -> str:
    if word.endswith("igst"):
        word = word[:-2]
    for suffix in _STEP3:
        if word.endswith(suffix) and len(word) - len(suffix) >= r1:
            if suffix == "løst":
                return word[:-1]
            return _consonant_pair(word[: -len(suffix)], r1)
    return word


def _undouble(word: str, r1: int) -> str:
    if len(word) >= 2 and len(word) - 1 >= r1:
        last = word[-1]
        if last not in _VOWELS and word[-2] == last:
            return word[:-1]
    return word


class CompoundSplitter:
    """Split Danish compounds into two known words.

    This is the frequency method from Koehn and Knight (2003): a split is
    used when the geometric mean of the part frequencies is higher than the
    frequency of the whole word. A linking "s" or "e" is allowed after the
    first part, as in "arbejd-s-dag".
    """

    def __init__(self, min_part: int = 3, min_word: int = 7) -> None:
        self.min_part = min_part
        self.min_word = min_word
        self._freq: Counter[str] = Counter()

    def fit(self, words: Iterable[str]) -> CompoundSplitter:
        self._freq = Counter(word.lower() for word in words if len(word) >= self.min_part)
        return self

    @property
    def vocabulary(self) -> Counter[str]:
        return self._freq

    def split(self, word: str) -> list[str]:
        word = word.lower()
        if len(word) < self.min_word or "-" in word:
            return []
        best: tuple[float, list[str]] = (float(self._freq.get(word, 0)), [])
        for i in range(self.min_part, len(word) - self.min_part + 1):
            right = word[i:]
            right_freq = self._freq.get(right, 0)
            if not right_freq:
                continue
            for left in _left_candidates(word[:i], self.min_part):
                left_freq = self._freq.get(left, 0)
                if not left_freq:
                    continue
                score = math.sqrt(left_freq * right_freq)
                if score > best[0]:
                    best = (score, [left, right])
        return best[1]


def _left_candidates(left: str, min_part: int) -> list[str]:
    candidates = [left]
    if left[-1] in "se" and len(left) - 1 >= min_part:
        candidates.append(left[:-1])
    if left[-1] == "s":
        # "arbejds" -> "arbejde": the linking s often replaces a final e
        candidates.append(left[:-1] + "e")
    return candidates
