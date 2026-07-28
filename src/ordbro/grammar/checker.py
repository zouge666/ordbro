"""A small grammar checker.

Each rule looks for one mistake that learners at A1-A2 often make. The
rules are explicit on purpose: every message can say exactly what is
wrong and which course note explains it, and a teacher can read the code.
A rule only fires when it is quite sure, so a missed mistake is more
likely than a false alarm.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from ordbro.content.lexicon import Lexicon
from ordbro.nlp.tokenize import Token, tokens_with_spans

RULES: dict[str, str] = {
    "capital-noun": "noun_gender",
    "capital-word": "pronouns",
    "article-gender": "noun_gender",
    "adjective-agreement": "adjectives",
    "double-definite": "definite_form",
    "modal-infinitive": "modal_verbs",
    "present-r": "present_tense",
    "v2-inversion": "word_order",
    "negation-placement": "negation",
    "past-irregular": "past_tense",
    "english-word": "",
}

SUBJECTS = {"jeg", "du", "han", "hun", "vi", "de", "man", "det", "den"}
MODALS = {"kan", "vil", "skal", "må", "bør"}
MID_ADVERBS = {"ikke", "aldrig", "altid", "også", "tit", "ofte", "gerne"}
SUBORDINATORS = {"fordi", "at", "når", "hvis", "selvom", "mens"}
COORDINATORS = {"og", "men", "eller"}
NUMBERS = {"to", "tre", "fire", "fem", "seks", "mange", "nogle", "alle"}
DAYS_MONTHS = set(
    "mandag tirsdag onsdag torsdag fredag lørdag søndag januar februar marts april maj juni "
    "juli august september oktober november december".split()
)
FRONTED = [
    phrase.split()
    for phrase in (
        "i dag",
        "i morgen",
        "i går",
        "i aften",
        "i weekenden",
        "i år",
        "om morgenen",
        "om aftenen",
        "om eftermiddagen",
        "hver dag",
        "nogle gange",
        "til sidst",
        "nu",
        "så",
        "derfor",
        "bagefter",
        "senere",
        "måske",
        "først",
        "tit",
        "ofte",
    )
]
ENGLISH = {
    "and": "og",
    "the": "-en / -et",
    "not": "ikke",
    "but": "men",
    "very": "meget",
    "because": "fordi",
    "with": "med",
}
_SENTENCE = re.compile(r"[^.!?\n]+[.!?]*")


@dataclass(frozen=True)
class Issue:
    rule: str
    message: str
    start: int
    end: int
    original: str
    suggestion: str
    skill: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GrammarChecker:
    def __init__(self, lexicon: Lexicon) -> None:
        self.lexicon = lexicon
        self._rules: list[Callable[[list[Token], str], list[Issue]]] = [
            self._capitals,
            self._article_and_adjective,
            self._double_definite,
            self._modal_infinitive,
            self._present_r,
            self._inversion,
            self._negation,
            self._past_irregular,
            self._english_words,
        ]

    def check(self, text: str) -> list[Issue]:
        issues: list[Issue] = []
        for match in _SENTENCE.finditer(text):
            tokens = [
                Token(t.text, t.start + match.start(), t.end + match.start())
                for t in tokens_with_spans(match.group(0))
            ]
            if not tokens:
                continue
            for rule in self._rules:
                issues.extend(rule(tokens, text))
        issues.sort(key=lambda issue: (issue.start, issue.rule))
        return _drop_overlaps(issues)

    # helpers ------------------------------------------------------------------

    def _issue(self, rule: str, message: str, text: str, start: int, end: int, fix: str) -> Issue:
        return Issue(rule, message, start, end, text[start:end], fix, RULES[rule])

    def _finite(self, token: Token) -> bool:
        word = token.lower
        return word in MODALS or self.lexicon.verb(word, ("present", "past")) is not None

    # rules --------------------------------------------------------------------

    def _capitals(self, tokens: list[Token], text: str) -> list[Issue]:
        issues = []
        for token in tokens[1:]:
            if not token.text[0].isupper() or token.text.isupper() or _after_quote(text, token):
                continue
            word = token.lower
            if word in DAYS_MONTHS:
                message = "Days and months are written with a small letter in Danish."
                rule = "capital-word"
            elif word == "jeg":
                message = "'jeg' is written with a small letter inside a sentence."
                rule = "capital-word"
            elif self.lexicon.noun(word) and not self.lexicon.verb(word):
                message = "Nouns are written with a small letter in Danish."
                rule = "capital-noun"
            else:
                continue
            issues.append(self._issue(rule, message, text, token.start, token.end, word))
        return issues

    def _article_and_adjective(self, tokens: list[Token], text: str) -> list[Issue]:
        issues = []
        for i, token in enumerate(tokens):
            word = token.lower
            if word not in {"en", "et", "den", "det", "de"} and word not in NUMBERS:
                continue
            j = i + 1
            adjectives = []
            while j < len(tokens) and self.lexicon.adjective(tokens[j].lower):
                adjectives.append(tokens[j])
                j += 1
            if j >= len(tokens):
                continue
            noun_hit = self.lexicon.noun(tokens[j].lower)
            if noun_hit is None:
                continue
            noun, kind = noun_hit
            if word in {"en", "et"} and kind == "da":
                if word != noun.gender:
                    issues.append(
                        self._issue(
                            "article-gender",
                            f"'{noun.da}' is an {noun.gender}-word. Use '{noun.gender}'.",
                            text,
                            token.start,
                            token.end,
                            _same_case(token.text, noun.gender),
                        )
                    )
                expected_kind = "t_form" if noun.gender == "et" else "da"
                message = f"With an {noun.gender}-word the adjective is '{{form}}'."
            elif word in NUMBERS and kind == "plural":
                expected_kind = "plural"
                message = "In the plural the adjective gets -e: '{form}'."
            elif word in {"den", "det", "de"} and adjectives and kind in {"da", "plural"}:
                expected_kind = "definite"
                message = "After den, det and de the adjective gets -e: '{form}'."
            else:
                continue
            for adj_token in adjectives:
                adj, _ = self.lexicon.adjective(adj_token.lower)
                expected = adj.forms().get(expected_kind, adj.da)
                if adj_token.lower != expected:
                    issues.append(
                        self._issue(
                            "adjective-agreement",
                            message.format(form=expected),
                            text,
                            adj_token.start,
                            adj_token.end,
                            expected,
                        )
                    )
        return issues

    def _double_definite(self, tokens: list[Token], text: str) -> list[Issue]:
        issues = []
        for i, token in enumerate(tokens[:-1]):
            if token.lower not in {"den", "det", "de"}:
                continue
            j = i + 1
            while j < len(tokens) and self.lexicon.adjective(tokens[j].lower):
                j += 1
            if j >= len(tokens):
                continue
            noun_hit = self.lexicon.noun(tokens[j].lower, ("definite", "plural_definite"))
            if noun_hit is None:
                continue
            noun, kind = noun_hit
            if j == i + 1:
                fix = _same_case(token.text, tokens[j].text)
                issues.append(
                    self._issue(
                        "double-definite",
                        f"Use the ending or den/det, not both: '{tokens[j].text}'.",
                        text,
                        token.start,
                        tokens[j].end,
                        fix,
                    )
                )
            else:
                base = noun.da if kind == "definite" else (noun.plural or noun.da)
                issues.append(
                    self._issue(
                        "double-definite",
                        f"After {token.lower} and an adjective the noun has no ending: '{base}'.",
                        text,
                        tokens[j].start,
                        tokens[j].end,
                        base,
                    )
                )
        return issues

    def _modal_infinitive(self, tokens: list[Token], text: str) -> list[Issue]:
        issues = []
        for i, token in enumerate(tokens):
            word = token.lower
            if word not in MODALS and word != "at":
                continue
            j = i + 1
            while j < len(tokens) and tokens[j].lower in MID_ADVERBS | {"godt", "bare", "lige"}:
                j += 1
            if j >= len(tokens) or (word == "at" and j != i + 1):
                continue
            hit = self.lexicon.verb(tokens[j].lower, ("present",))
            if hit is None or self.lexicon.noun(tokens[j].lower):
                continue
            verb, _ = hit
            if verb.da == tokens[j].lower or verb.group == "modal":
                continue
            trigger = "at" if word == "at" else word
            issues.append(
                self._issue(
                    "modal-infinitive",
                    f"After '{trigger}' the verb is in the infinitive: '{verb.da}'.",
                    text,
                    tokens[j].start,
                    tokens[j].end,
                    verb.da,
                )
            )
        return issues

    def _present_r(self, tokens: list[Token], text: str) -> list[Issue]:
        issues = []
        for i in _clause_starts(tokens):
            if i + 1 >= len(tokens) or tokens[i].lower not in SUBJECTS:
                continue
            nxt = tokens[i + 1]
            hit = self.lexicon.verb(nxt.lower, ("da",))
            if hit is None or self.lexicon.verb(nxt.lower, ("present", "past")):
                continue
            verb, _ = hit
            if verb.group == "modal" or not verb.present:
                continue
            issues.append(
                self._issue(
                    "present-r",
                    f"The present tense of '{verb.da}' is '{verb.present}'.",
                    text,
                    nxt.start,
                    nxt.end,
                    verb.present,
                )
            )
        return issues

    def _inversion(self, tokens: list[Token], text: str) -> list[Issue]:
        lowered = [t.lower for t in tokens]
        start = None
        for phrase in FRONTED:
            if lowered[: len(phrase)] == phrase:
                start = len(phrase)
                break
        if start is None and lowered[0] in SUBORDINATORS | {"når"}:
            sentence_end = tokens[-1].end
            comma = text.find(",", tokens[0].start, sentence_end)
            if comma < 0:
                return []
            start = next((k for k, t in enumerate(tokens) if t.start > comma), None)
        if start is None or start + 1 >= len(tokens):
            return []
        subject, verb = tokens[start], tokens[start + 1]
        if subject.lower not in SUBJECTS or not self._finite(verb):
            return []
        return [
            self._issue(
                "v2-inversion",
                "The verb must be in second place. Put the verb before the subject.",
                text,
                subject.start,
                verb.end,
                f"{verb.text} {subject.text}",
            )
        ]

    def _negation(self, tokens: list[Token], text: str) -> list[Issue]:
        issues = []
        for i, token in enumerate(tokens[:-3]):
            if token.lower not in SUBORDINATORS:
                continue
            subject, verb, adverb = tokens[i + 1], tokens[i + 2], tokens[i + 3]
            if subject.lower not in SUBJECTS or adverb.lower not in MID_ADVERBS:
                continue
            if not self._finite(verb):
                continue
            issues.append(
                self._issue(
                    "negation-placement",
                    f"In a subordinate clause '{adverb.lower}' comes before the verb.",
                    text,
                    verb.start,
                    adverb.end,
                    f"{adverb.text} {verb.text}",
                )
            )
        return issues

    def _past_irregular(self, tokens: list[Token], text: str) -> list[Issue]:
        issues = []
        for token in tokens:
            right = self.lexicon.wrong_past(token.lower)
            if right:
                issues.append(
                    self._issue(
                        "past-irregular",
                        f"This verb is irregular. The past tense is '{right}'.",
                        text,
                        token.start,
                        token.end,
                        _same_case(token.text, right),
                    )
                )
        return issues

    def _english_words(self, tokens: list[Token], text: str) -> list[Issue]:
        danish = sum(1 for t in tokens if self.lexicon.is_known(t.lower) or t.lower in SUBJECTS)
        if danish < 2:
            return []
        return [
            self._issue(
                "english-word",
                f"This looks like an English word. In Danish: '{ENGLISH[t.lower]}'.",
                text,
                t.start,
                t.end,
                ENGLISH[t.lower],
            )
            for t in tokens
            if t.lower in ENGLISH and t.text != "I"
        ]


def apply_suggestions(text: str, issues: list[Issue]) -> str:
    """Return the text with all suggestions applied (last one first)."""
    output = text
    for issue in sorted(issues, key=lambda item: item.start, reverse=True):
        if issue.rule == "english-word" and issue.suggestion.startswith("-"):
            continue
        output = output[: issue.start] + issue.suggestion + output[issue.end :]
    return output


def _clause_starts(tokens: list[Token]) -> list[int]:
    starts = [0]
    for i, token in enumerate(tokens[:-1]):
        if token.lower in SUBORDINATORS | COORDINATORS:
            starts.append(i + 1)
    return starts


def _after_quote(text: str, token: Token) -> bool:
    before = text[max(0, token.start - 2) : token.start]
    return any(mark in before for mark in "\"“”'«:")


def _same_case(original: str, word: str) -> str:
    return word[:1].upper() + word[1:] if original[:1].isupper() else word


def _drop_overlaps(issues: list[Issue]) -> list[Issue]:
    kept: list[Issue] = []
    for issue in issues:
        if kept and issue.start < kept[-1].end and issue.rule == kept[-1].rule:
            continue
        kept.append(issue)
    return kept
