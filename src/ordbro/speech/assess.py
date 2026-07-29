"""Compare what the recognizer heard with the sentence the learner read.

The score is about being understood. A word counts as "ok" when the
recognizer heard it, "close" when it heard a similar word, and "missed"
when it heard nothing like it. This is a proxy: a recognizer can fail on a
well pronounced word, so the app always shows what was heard and never uses
the score for grading.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from ordbro.nlp.distance import align, cer, similarity, wer
from ordbro.speech.hints import hints_for

_WORD = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*")
_NUMBERS = dict(
    enumerate(
        "nul en to tre fire fem seks syv otte ni ti elleve tolv tretten fjorten femten seksten "
        "sytten atten nitten tyve".split()
    )
)
CLOSE_AT = 0.6


@dataclass
class WordResult:
    target: str | None
    heard: str | None
    status: str
    similarity: float
    hints: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Assessment:
    target: str
    transcript: str
    words: list[WordResult]
    score: int
    word_accuracy: float
    wer: float
    cer: float
    tips: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def words(text: str) -> list[str]:
    output = []
    for match in _WORD.finditer(text.lower()):
        token = match.group(0)
        output.append(
            _NUMBERS.get(int(token), token) if token.isdigit() and int(token) <= 20 else token
        )
    return output


def assess(target: str, transcript: str) -> Assessment:
    ref = words(target)
    hyp = words(transcript)
    shown = _WORD.findall(target)
    steps = align(ref, hyp, lambda a, b: 1.0 - similarity(a, b))
    results: list[WordResult] = []
    for step in steps:
        if step.op == "ins":
            results.append(WordResult(None, hyp[step.hyp], "extra", 0.0))
            continue
        word = shown[step.ref] if step.ref < len(shown) else ref[step.ref]
        if step.op == "match":
            results.append(WordResult(word, hyp[step.hyp], "ok", 1.0))
            continue
        heard = hyp[step.hyp] if step.op == "sub" else None
        sim = similarity(ref[step.ref], heard) if heard else 0.0
        status = "close" if heard and sim >= CLOSE_AT else "missed"
        hints = [hint.to_dict() for hint in hints_for(ref[step.ref])]
        results.append(WordResult(word, heard, status, round(sim, 3), hints))

    total = max(len(ref), 1)
    ok = sum(1 for r in results if r.status == "ok")
    close = sum(1 for r in results if r.status == "close")
    extra = sum(1 for r in results if r.status == "extra")
    raw = (ok + 0.5 * close - 0.25 * min(extra, 2)) / total
    tips: list[dict[str, str]] = []
    for result in results:
        for hint in result.hints:
            if hint["id"] not in {tip["id"] for tip in tips}:
                tips.append(hint)
    return Assessment(
        target=target,
        transcript=transcript,
        words=results,
        score=max(0, min(100, round(raw * 100))),
        word_accuracy=round(ok / total, 3),
        wer=round(wer(ref, hyp), 3),
        cer=round(cer(" ".join(ref), " ".join(hyp)), 3),
        tips=tips[:3],
    )
