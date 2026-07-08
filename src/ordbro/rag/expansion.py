"""English to Danish query expansion with a small glossary.

Learners often ask in English while the course notes are in Danish. The
glossary maps grammar words ("past tense") and common words ("bakery") to
the Danish words that the notes use ("datid", "bager").
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ordbro.nlp.tokenize import tokenize

_MAX_WORDS = 4


class GlossaryExpander:
    def __init__(self, entries: Mapping[str, Sequence[str]]) -> None:
        self._entries = {
            tuple(tokenize(key)): [term for term in values if term]
            for key, values in entries.items()
            if tokenize(key)
        }

    def __len__(self) -> int:
        return len(self._entries)

    def expand(self, query: str) -> tuple[list[str], list[str]]:
        """Return (Danish terms to add, glossary keys that matched)."""
        tokens = tokenize(query)
        added: list[str] = []
        matched: list[str] = []
        i = 0
        while i < len(tokens):
            hit = None
            for size in range(min(_MAX_WORDS, len(tokens) - i), 0, -1):
                window = tuple(tokens[i : i + size])
                for candidate in (window, tuple(_singular(t) for t in window)):
                    if candidate in self._entries:
                        hit = (size, candidate)
                        break
                if hit:
                    break
            if hit:
                size, key = hit
                matched.append(" ".join(key))
                for term in self._entries[key]:
                    if term not in added:
                        added.append(term)
                i += size
            else:
                i += 1
        return added, matched


def _singular(token: str) -> str:
    if len(token) > 3 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token
