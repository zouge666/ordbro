"""Drills generated from the vocabulary list.

Generated items are form drills: they do not need a context sentence, so
they are always correct as long as the vocabulary list is correct.
"""

from __future__ import annotations

import random

from ordbro.content.lexicon import Lexicon, VocabEntry
from ordbro.exercises.models import Exercise

# nouns that make sense with colour and size adjectives
_THINGS = ("hus", "bil", "bord", "stol", "cykel", "bog", "jakke", "telefon", "æble", "værelse")
_DESCRIBING = ("stor", "lille", "ny", "gammel", "rød", "grøn", "hvid", "sort", "billig", "dyr")


def generate_exercises(lexicon: Lexicon, seed: int = 7) -> list[Exercise]:
    rng = random.Random(seed)
    items: list[Exercise] = []
    nouns = lexicon.by_pos("noun")
    for noun in nouns:
        items.append(_gender(noun))
        items.append(_definite(noun))
        if noun.plural:
            items.append(_plural(noun))
    for verb in lexicon.by_pos("verb"):
        items.extend(_verb_forms(verb))
    for adj_base in _DESCRIBING:
        adj = lexicon.word(adj_base, "adj")
        for noun_base in _THINGS:
            noun = lexicon.word(noun_base, "noun")
            if adj and noun:
                items.append(_adjective(adj, noun, plural=False))
                if noun.plural:
                    items.append(_adjective(adj, noun, plural=True))
    for adj in lexicon.by_pos("adj"):
        if adj.comparative and adj.superlative and " " not in adj.comparative:
            items.append(_comparison(adj))
    entries = [e for e in lexicon.entries if e.pos in {"noun", "verb", "adj", "other"}]
    for entry in entries:
        items.append(_card_da_en(entry, entries, rng))
        items.append(_card_en_da(entry))
    return items


def _gender(noun: VocabEntry) -> Exercise:
    return Exercise(
        id=f"gen:gender:{noun.da}",
        skill="noun_gender",
        type="choice",
        prompt=f"Choose the article for '{noun.da}' ({noun.en}).",
        text=f"___ {noun.da}",
        options=("en", "et"),
        answers=(noun.gender or "en",),
        hint="Many short words for things are et-words, and words for people are often en-words.",
        explanation=f"It is {noun.gender} {noun.da}: {noun.definite}, {noun.plural or noun.da}.",
        speak=f"{noun.gender} {noun.da}",
    )


def _definite(noun: VocabEntry) -> Exercise:
    ending = "-n" if noun.da.endswith("e") and noun.gender == "en" else f"-{noun.gender}"
    if noun.da.endswith("e") and noun.gender == "et":
        ending = "-t"
    return Exercise(
        id=f"gen:definite:{noun.da}",
        skill="definite_form",
        type="form",
        prompt=f"Write 'the {noun.en.split(',')[0]}' in Danish.",
        text=f"{noun.gender} {noun.da} → ___",
        answers=(noun.definite or noun.da,),
        hint=f"{noun.da.capitalize()} is an {noun.gender}-word. It gets {ending}.",
        explanation=f"{noun.gender} {noun.da} → {noun.definite}.",
        speak=noun.definite or noun.da,
    )


def _plural(noun: VocabEntry) -> Exercise:
    regular = {noun.da + "er", noun.da + "e", noun.da + "r", noun.da}
    hint = (
        "This plural is irregular. The vowel can change."
        if noun.plural not in regular
        else "The plural ends in -er, -e or has no ending."
    )
    return Exercise(
        id=f"gen:plural:{noun.da}",
        skill="plural",
        type="form",
        prompt=f"Write the plural of '{noun.gender} {noun.da}' ({noun.en}).",
        text=f"en/et {noun.da} → to ___",
        answers=(noun.plural or noun.da,),
        hint=hint,
        explanation=", ".join(
            [
                f"{noun.gender} {noun.da}",
                noun.definite or "",
                noun.plural or "",
                noun.plural_definite or "",
            ]
        )
        + ".",
        speak=noun.plural or noun.da,
    )


def _verb_forms(verb: VocabEntry) -> list[Exercise]:
    group_hint = {
        "1": "This verb is in group 1. The past tense ends in -ede.",
        "2": "This verb is in group 2. The past tense ends in -te.",
    }.get(verb.group or "", "This verb is irregular. Look at the list in your notes.")
    items = [
        Exercise(
            id=f"gen:present:{verb.da}",
            skill="present_tense",
            type="form",
            prompt=f"Write the present tense of 'at {verb.da}' ({verb.en}).",
            text=f"at {verb.da} → jeg ___",
            answers=(verb.present or "",),
            hint="Most verbs add -r to the infinitive."
            if verb.present == verb.da + "r"
            else "This verb is irregular in the present tense.",
            explanation=f"at {verb.da} → jeg {verb.present}.",
            speak=f"jeg {verb.present}",
        ),
    ]
    if verb.group != "modal":
        items.append(
            Exercise(
                id=f"gen:past:{verb.da}",
                skill="past_tense",
                type="form",
                prompt=f"Write the past tense of 'at {verb.da}' ({verb.en}).",
                text=f"i går ___ jeg ... (at {verb.da})",
                answers=(verb.past or "",),
                hint=group_hint,
                explanation=f"{verb.da}, {verb.present}, {verb.past}, {verb.aux} {verb.perfect}.",
                level="A2",
                speak=f"i går {verb.past} jeg",
            )
        )
        items.append(
            Exercise(
                id=f"gen:perfect:{verb.da}",
                skill="perfect_tense",
                type="form",
                prompt=f"Write the participle of 'at {verb.da}'.",
                text=f"jeg {verb.aux} ___ (at {verb.da})",
                answers=(verb.perfect or "",),
                hint="The participle often ends in -t or -et.",
                explanation=f"jeg {verb.aux} {verb.perfect}.",
                level="A2",
                speak=f"jeg {verb.aux} {verb.perfect}",
            )
        )
    return items


def _adjective(adj: VocabEntry, noun: VocabEntry, plural: bool) -> Exercise:
    forms = tuple(dict.fromkeys([adj.da, adj.t_form or adj.da, adj.plural or adj.da]))
    if plural:
        answer = adj.plural or adj.da
        text = f"to ___ {noun.plural}"
        why = f"{noun.plural} is plural, so the adjective is {answer}."
    else:
        answer = adj.t_form if noun.gender == "et" else adj.da
        text = f"{noun.gender} ___ {noun.da}"
        why = f"{noun.da} is an {noun.gender}-word, so it is {noun.gender} {answer} {noun.da}."
    options = forms if len(forms) > 1 else (adj.da, adj.da + "t", adj.da + "e")
    return Exercise(
        id=f"gen:adj:{adj.da}:{noun.da}:{'pl' if plural else 'sg'}",
        skill="adjectives",
        type="choice",
        prompt=f"Choose the right form of '{adj.da}' ({adj.en}).",
        text=text,
        options=options,
        answers=(answer or adj.da,),
        hint="Look at the noun: is it an en-word, an et-word or plural?",
        explanation=why,
        level="A2",
        speak=text.replace("___", answer or adj.da),
    )


def _comparison(adj: VocabEntry) -> Exercise:
    return Exercise(
        id=f"gen:compare:{adj.da}",
        skill="comparison",
        type="form",
        prompt=f"Write the comparative of '{adj.da}' ({adj.en}).",
        text=f"{adj.da}, ___, {adj.superlative}",
        answers=(adj.comparative or "",),
        hint="Most adjectives add -ere. Some common ones are irregular.",
        explanation=f"{adj.da}, {adj.comparative}, {adj.superlative}.",
        level="A2",
        speak=f"{adj.da}, {adj.comparative}, {adj.superlative}",
    )


def _card_da_en(entry: VocabEntry, pool: list[VocabEntry], rng: random.Random) -> Exercise:
    same_pos = [e for e in pool if e.pos == entry.pos and e.en != entry.en]
    distractors = rng.sample(same_pos, k=min(3, len(same_pos)))
    options = [entry.en, *(e.en for e in distractors)]
    rng.shuffle(options)
    shown = f"{entry.gender} {entry.da}" if entry.pos == "noun" else entry.da
    return Exercise(
        id=f"card:da-en:{entry.pos}:{entry.da}",
        skill="",
        type="flashcard",
        prompt="What does this word mean?",
        text=shown,
        options=tuple(options),
        answers=(entry.en,),
        explanation=f"{shown} = {entry.en}",
        level=entry.level,
        card_id=entry.id,
        speak=shown,
        tags=(entry.topic,),
    )


def _card_en_da(entry: VocabEntry) -> Exercise:
    answers = [entry.da]
    if entry.pos == "noun" and entry.gender:
        answers.append(f"{entry.gender} {entry.da}")
    if entry.pos == "verb":
        answers.append(f"at {entry.da}")
    return Exercise(
        id=f"card:en-da:{entry.pos}:{entry.da}",
        skill="",
        type="translate",
        prompt=f"Write in Danish: '{entry.en}'",
        answers=tuple(answers),
        hint=f"It starts with '{entry.da[0]}' and has {len(entry.da)} letters.",
        explanation=f"{entry.en} = {answers[-1]}",
        level=entry.level,
        card_id=entry.id,
        speak=entry.da,
        tags=(entry.topic,),
    )
