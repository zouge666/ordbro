import pytest

from ordbro.rag import parse_markdown

WORD_ORDER = """---
title: Ordstilling
title_en: Word order
level: A1
summary_en: The verb is always the second element in a main clause.
---
# Ordstilling

## Regel
Verbet står altid på plads nummer 2 i en hovedsætning.
Hvis sætningen starter med noget andet end subjektet, kommer verbet før subjektet.

## Eksempler
- Jeg går i skole i dag.
- I dag går jeg i skole.
"""

GENDER = """---
title: En-ord og et-ord
title_en: Noun gender
level: A1
summary_en: Danish nouns are either en-words or et-words.
---
# En-ord og et-ord

## Regel
Et navneord er enten et en-ord eller et et-ord. Lær altid ordet sammen med en eller et.

## Eksempler
- en bil, en pige, en stol
- et hus, et barn, et æble
"""

PAST = """---
title: Datid
title_en: Past tense
level: A2
summary_en: How to make the past tense of regular and irregular verbs.
---
# Datid

## Regel
Mange verber får -ede eller -te i datid: lave, lavede. Spise, spiste.

## Uregelmæssige verber
Nogle verber er uregelmæssige: gå, gik. Se, så. Få, fik. Være, var.
"""


@pytest.fixture
def mini_docs():
    return [
        parse_markdown("ordstilling", WORD_ORDER),
        parse_markdown("koen", GENDER),
        parse_markdown("datid", PAST),
    ]


@pytest.fixture
def mini_glossary():
    return {
        "word order": ["ordstilling", "inversion"],
        "subject": ["subjekt", "subjektet"],
        "verb": ["verbum", "verbet"],
        "past tense": ["datid"],
        "irregular": ["uregelmæssige"],
        "noun": ["navneord"],
        "gender": ["en-ord", "et-ord"],
    }
