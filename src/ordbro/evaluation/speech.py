"""A simulation study: how recognition errors change pronunciation feedback.

There is no recorded learner speech in this project, so the study uses a
simple noise model. A recognizer turns each spoken word into a near miss
("hedder" -> "heder"), drops it, or hears another word, with probability
``rate``. The n-best list is drawn from the same model.

Two speakers are simulated:

* a speaker who says every word right. Every flagged word is a false alarm,
  so this measures how unfair the feedback can be when the recognizer is
  weak, for example with an accent it was not trained on;
* a learner with one real mistake. The mistake is in the audio, so the
  recognizer hears a different word. But a recognizer also has a language
  model that prefers likely sentences, so sometimes it "hears" the word the
  learner meant to say (``lm_fix``). This measures whether the feedback
  still finds the real mistake.

The study compares using only the first transcript with picking the best of
three alternatives. The numbers depend on the assumed noise model.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Any

from ordbro.evaluation.metrics import mean
from ordbro.nlp.distance import similarity
from ordbro.speech import assess, words

_CONFUSIONS = (("hv", "v"), ("d", ""), ("ø", "o"), ("æ", "e"), ("å", "a"), ("g", ""), ("r", ""))


def near_miss(word: str, rng: random.Random) -> str:
    options = [(a, b) for a, b in _CONFUSIONS if a in word and len(word) > len(a)]
    if options:
        a, b = rng.choice(options)
        return word.replace(a, b, 1)
    if len(word) > 3:
        i = rng.randrange(1, len(word))
        return word[:i] + word[i + 1 :]
    return word + "n"


def mistake(word: str, vocabulary: Sequence[str], rng: random.Random) -> str:
    """A learner error that the recognizer hears as a clearly different word."""
    pool = [w for w in vocabulary if w != word and similarity(w, word) < 0.5]
    return rng.choice(pool) if pool else word[::-1]


def recognize(spoken: list[str], rate: float, vocabulary: Sequence[str], rng: random.Random) -> str:
    heard = []
    for word in spoken:
        roll = rng.random()
        if roll >= rate:
            heard.append(word)
            continue
        kind = rng.random()
        if kind < 0.5:
            heard.append(near_miss(word, rng))
        elif kind < 0.75:
            continue
        else:
            heard.append(rng.choice(vocabulary))
    return " ".join(heard)


def simulate(
    sentences: Sequence[str],
    vocabulary: Sequence[str],
    rates: Sequence[float] = (0.0, 0.05, 0.1, 0.2, 0.3),
    n_best: Sequence[int] = (1, 3),
    lm_fix: Sequence[float] = (0.0, 0.25),
    trials: int = 30,
    seed: int = 13,
) -> dict[str, Any]:
    rows = []
    for rate, n, fix in ((r, n, f) for r in rates for n in n_best for f in lm_fix):
        rng = random.Random(f"{seed}-{rate}-{n}-{fix}")
        false_flags, scores, found, precision = [], [], [], []
        for _ in range(trials):
            for sentence in sentences:
                target = words(sentence)
                alts = [recognize(target, rate, vocabulary, rng) for _ in range(n)]
                result = assess(sentence, alts[0], alts[1:])
                flagged = [w for w in result.words if w.status in {"close", "missed"}]
                false_flags.append(len(flagged) / len(target))
                scores.append(result.score)

                k = rng.randrange(len(target))
                spoken = list(target)
                spoken[k] = mistake(target[k], vocabulary, rng)
                alts = []
                for _ in range(n):
                    heard = list(spoken)
                    if rng.random() < fix:
                        heard[k] = target[k]
                    alts.append(recognize(heard, rate, vocabulary, rng))
                result = assess(sentence, alts[0], alts[1:])
                target_results = [w for w in result.words if w.target is not None]
                hit = target_results[k].status in {"close", "missed"}
                flagged = [w for w in target_results if w.status in {"close", "missed"}]
                found.append(float(hit))
                precision.append((1.0 if hit else 0.0) / len(flagged) if flagged else 0.0)
        rows.append(
            {
                "rate": rate,
                "n_best": n,
                "lm_fix": fix,
                "false_flags_per_word": round(mean(false_flags), 4),
                "mean_score_correct_speaker": round(mean(scores), 2),
                "mistake_found": round(mean(found), 4),
                "flag_precision": round(mean(precision), 4),
            }
        )
    return {"sentences": len(sentences), "trials": trials, "rows": rows}
