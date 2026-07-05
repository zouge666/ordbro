import pytest

from ordbro.nlp import CompoundSplitter, DanishAnalyzer, DanishStemmer, LegacyAnalyzer
from ordbro.nlp.analyzers import guess_language
from ordbro.nlp.distance import align, cer, levenshtein, similarity, wer
from ordbro.nlp.tokenize import sentences, tokenize, tokens_with_spans


def test_tokenize_keeps_danish_letters():
    assert tokenize("Jeg går på arbejde i Brøndby.") == [
        "jeg",
        "går",
        "på",
        "arbejde",
        "i",
        "brøndby",
    ]


def test_tokens_with_spans_keep_case_and_offsets():
    tokens = tokens_with_spans("I dag går jeg")
    assert [t.text for t in tokens] == ["I", "dag", "går", "jeg"]
    assert tokens[2].start == 6 and tokens[2].end == 9


def test_sentences_split_on_end_marks_and_lines():
    text = "Jeg hedder Anna. Hvad hedder du?\nJeg bor i Aarhus"
    assert sentences(text) == ["Jeg hedder Anna.", "Hvad hedder du?", "Jeg bor i Aarhus"]


def test_legacy_analyzer_breaks_words_with_danish_letters():
    # This is the behaviour of the original pipeline that Ordbro fixes.
    assert LegacyAnalyzer().index_terms("går på") == ["g", "r", "p"]


def test_legacy_query_terms_follow_original_rules():
    analyzer = LegacyAnalyzer()
    assert analyzer.query_terms("What is the past tense of the verb?") == [
        "past",
        "tense",
        "verb",
    ]
    assert analyzer.query_terms("is a") == ["is", "a"]


@pytest.mark.parametrize(
    ("word", "stem"),
    [
        ("huset", "hus"),
        ("husene", "hus"),
        ("bilerne", "bil"),
        ("kattene", "kat"),
        ("spiser", "spis"),
        ("spise", "spis"),
        ("pigen", "pig"),
        ("købte", "købt"),
        ("lærerne", "lær"),
        ("hurtigst", "hurt"),
        ("arbejdsdag", "arbejdsdag"),
        ("på", "på"),
    ],
)
def test_snowball_stemmer(word, stem):
    assert DanishStemmer().stem(word) == stem


def test_compound_splitter_uses_part_frequencies():
    splitter = CompoundSplitter().fit(
        ["tog", "tog", "station", "station", "arbejde", "dag", "dag", "hus", "syge", "sygehus"]
    )
    assert splitter.split("togstation") == ["tog", "station"]
    assert splitter.split("arbejdsdag") == ["arbejde", "dag"]
    assert splitter.split("sygehus") == []
    assert splitter.split("station") == []


def test_danish_analyzer_drops_english_fillers_and_doubles_quoted_words():
    analyzer = DanishAnalyzer()
    analyzer.fit(["Jeg spiser ikke kød."])
    assert analyzer.query_terms("When do I use 'ikke'?") == ["use", "ikk", "ikk"]


def test_danish_analyzer_keeps_lowercase_i_as_a_danish_word():
    analyzer = DanishAnalyzer(stem=False, split_compounds=False)
    assert analyzer.query_terms("When do I say i or på?") == ["say", "i", "på"]


def test_ascii_spelling_is_mapped_to_danish_letters():
    analyzer = DanishAnalyzer(stem=False, split_compounds=False)
    analyzer.fit(["Jeg går på arbejde. Det er en stor bæk."])
    assert analyzer.fix_ascii("gaar") == "går"
    assert analyzer.fix_ascii("paa") == "på"
    assert analyzer.fix_ascii("baek") == "bæk"
    assert analyzer.fix_ascii("unknown") == "unknown"


def test_index_terms_include_compound_parts():
    analyzer = DanishAnalyzer(stem=False)
    analyzer.fit(["tog tog station station togstation"])
    assert analyzer.index_terms("togstation") == ["togstation", "tog", "station"]


def test_guess_language():
    assert guess_language("Hvornår bruger man inversion".split()) == "da"
    assert guess_language("When do I use inversion".split()) == "en"


def test_levenshtein_and_similarity():
    assert levenshtein("kitten", "sitting") == 3
    assert similarity("hus", "hus") == 1.0
    assert similarity("", "") == 1.0
    assert 0.0 < similarity("hedder", "heder") < 1.0


def test_wer_and_cer():
    assert wer(["jeg", "hedder", "anna"], ["jeg", "heder", "anna"]) == pytest.approx(1 / 3)
    assert wer([], []) == 0.0
    assert cer("hus", "huse") == pytest.approx(1 / 3)


def test_align_reports_missing_and_extra_words():
    steps = align(["jeg", "bor", "i", "aarhus"], ["jeg", "i", "aarhus", "nu"])
    assert [s.op for s in steps] == ["match", "del", "match", "match", "ins"]


def test_align_with_soft_cost_pairs_similar_words():
    steps = align(
        ["hvad", "hedder", "du"], ["vad", "heder", "du"], lambda a, b: 1 - similarity(a, b)
    )
    assert [s.op for s in steps] == ["sub", "sub", "match"]
