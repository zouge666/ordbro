import json

from ordbro.config import load_settings
from ordbro.content import load_content
from ordbro.speech import assess, hints_for, words


def ids(word):
    return [hint.id for hint in hints_for(word)]


def test_hints_follow_spelling_patterns():
    assert "silent-h" in ids("hvad")
    assert "soft-d" in ids("mad") and "soft-d" in ids("hedder")
    assert "silent-d" in ids("hund") and "soft-d" not in ids("hund")
    assert "stød" in ids("hund")
    assert "soft-g" in ids("dag") and "soft-g" in ids("pige")
    assert "vowels" in ids("rød")
    assert ids("tak") == []


def test_hint_sections_exist_in_the_pronunciation_note():
    content = load_content(load_settings().data_path)
    note = content.document("a1-udtale")
    section_ids = {section.id for section in note.sections}
    for word in ["hvad", "hund", "mad", "dag", "mor", "rød"]:
        for hint in hints_for(word):
            assert hint.section in section_ids, hint.section


def test_perfect_transcript():
    result = assess("Hvad hedder du?", "hvad hedder du")
    assert result.score == 100 and result.wer == 0.0
    assert {w.status for w in result.words} == {"ok"}
    assert result.tips == []


def test_close_and_missed_words_get_hints():
    result = assess("Hvad hedder du?", "vad heder")
    statuses = [(w.target, w.status) for w in result.words]
    assert statuses == [("Hvad", "close"), ("hedder", "close"), ("du", "missed")]
    assert result.tips[0]["id"] == "silent-h"
    assert 0 < result.score < 100


def test_extra_words_lower_the_score():
    assert assess("Tak for mad.", "tak tak for mad ja").score < 100


def test_digits_from_the_recognizer_count_as_words():
    assert words("Klokken er halv 3") == ["klokken", "er", "halv", "tre"]
    assert assess("Klokken er halv tre.", "klokken er halv 3").score == 100


def test_speaking_sentences_are_valid():
    items = json.loads((load_settings().data_path / "speaking.json").read_text(encoding="utf-8"))
    assert len(items) >= 20
    assert all(item["text"] and item["en"] and item["level"] in {"A1", "A2"} for item in items)
