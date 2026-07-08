import math

import pytest

from ordbro.rag import Answerer, KnowledgeBase, get_preset, parse_markdown
from ordbro.rag.chunking import RecursiveChunker, RecursiveSplitter, SectionChunker
from ordbro.rag.expansion import GlossaryExpander
from ordbro.rag.fusion import rrf
from ordbro.rag.sparse import BM25Index
from ordbro.rag.vectors import HashEmbedder, SubwordVectorizer, cosine


def test_front_matter_and_sections(mini_docs):
    doc = mini_docs[0]
    assert doc.title == "Ordstilling"
    assert doc.metadata["title_en"] == "Word order"
    assert [s.id for s in doc.sections] == ["ordstilling#regel", "ordstilling#eksempler"]
    rule = doc.section("ordstilling#regel")
    assert "plads nummer 2" in doc.section_text(rule)


def test_intro_text_becomes_its_own_section():
    doc = parse_markdown("x", "# Titel\nKort intro.\n\n## Regel\nTekst.\n")
    assert [s.id for s in doc.sections] == ["x#intro", "x#regel"]


def test_list_keys_in_front_matter():
    doc = parse_markdown("x", "---\ntitle: X\ntags: a, b , c\n---\n# X\n")
    assert doc.metadata["tags"] == ["a", "b", "c"]


def test_recursive_splitter_respects_size():
    text = "\n\n".join(f"Afsnit {i}. " + "ord " * 60 for i in range(20))
    pieces = RecursiveSplitter(800, 100).split_text(text)
    assert len(pieces) > 1
    assert all(len(piece) <= 800 for piece in pieces)


def test_section_chunker_adds_metadata_prefix(mini_docs):
    chunks = SectionChunker().chunk(mini_docs[0], metadata_prefix=True)
    rule = next(c for c in chunks if c.section_ids == ("ordstilling#regel",))
    assert rule.index_text.startswith("Ordstilling | Word order | Regel")
    assert "second element" in rule.index_text
    assert "second element" not in rule.text


def test_recursive_chunker_records_overlapping_sections(mini_docs):
    chunks = RecursiveChunker().chunk(mini_docs[0])
    assert len(chunks) == 1
    assert "ordstilling#regel" in chunks[0].section_ids
    assert "ordstilling#eksempler" in chunks[0].section_ids


def test_legacy_idf_goes_negative_for_common_terms():
    docs = {"a": ["en", "bil"], "b": ["en", "hus"], "c": ["en", "pige"]}
    legacy = BM25Index(idf="legacy")
    legacy.build(docs)
    fixed = BM25Index(idf="robertson")
    fixed.build(docs)
    assert legacy.idf("en") < 0
    assert fixed.idf("en") > 0


def test_bm25_ranks_matching_document_first():
    index = BM25Index()
    index.build({"a": ["bil", "rød"], "b": ["hus", "stor"], "c": ["bil", "hus"]})
    assert index.search(["bil", "rød"], top_k=2)[0][0] == "a"
    assert [doc for doc, _ in index.search(["hus"], top_k=5, allowed={"b"})] == ["b"]


def test_subword_vectors_link_inflected_forms():
    vectorizer = SubwordVectorizer()
    vectorizer.fit(["huset er stort", "bilen er rød", "husene er gamle"])
    hus, huset, bil = (vectorizer.transform(w) for w in ("hus", "huset", "bil"))
    assert cosine(hus, huset) > cosine(hus, bil)
    assert math.isclose(cosine(huset, huset), 1.0, rel_tol=1e-9)


def test_hash_embedder_is_deterministic_but_not_semantic():
    embedder = HashEmbedder(dimensions=64)
    a1, a2, b = embedder.embed(["huset", "huset", "husene"])
    assert a1 == a2
    assert math.isclose(sum(v * v for v in a1), 1.0, rel_tol=1e-9)
    assert abs(sum(x * y for x, y in zip(a1, b, strict=True))) < 0.5


def test_rrf_merges_rankings_and_breaks_ties_by_id():
    fused = rrf({"a": [("x", 3.0), ("y", 2.0)], "b": [("y", 0.9), ("z", 0.1)]}, k=60)
    assert [item for item, _ in fused] == ["y", "x", "z"]
    assert fused[0][1] == pytest.approx(1 / 62 + 1 / 61)


def test_glossary_expansion_matches_phrases_and_plurals(mini_glossary):
    expander = GlossaryExpander(mini_glossary)
    added, matched = expander.expand("How do I make the past tense of irregular verbs?")
    assert matched == ["past tense", "irregular", "verb"]
    assert added == ["datid", "uregelmæssige", "verbum", "verbet"]


def test_ordbro_preset_finds_word_order_rule_from_english_question(mini_docs, mini_glossary):
    kb = KnowledgeBase(mini_docs, "ordbro", glossary=mini_glossary)
    result = kb.search("When does the verb come before the subject?", top_k=3)
    assert result.hits[0].chunk.doc_id == "ordstilling"
    assert [stage["stage"] for stage in result.trace["stages"]][:3] == [
        "analyze",
        "bm25",
        "subword",
    ]


def test_legacy_preset_cannot_match_words_with_danish_letters(mini_docs):
    legacy = KnowledgeBase(mini_docs, "c0")
    ordbro = KnowledgeBase(mini_docs, "c2")
    assert legacy.analyzer.query_terms("gik") == ["gik"]
    assert legacy.analyzer.query_terms("så") == ["s"]
    assert ordbro.search("så", top_k=1).hits[0].chunk.doc_id == "datid"


def test_filters_are_applied_before_fusion_in_new_presets(mini_docs):
    kb = KnowledgeBase(mini_docs, "ordbro")
    result = kb.search("verber", top_k=3, filters={"level": "A2"})
    assert result.hits
    assert {hit.chunk.metadata["level"] for hit in result.hits} == {"A2"}


def test_answerer_gives_lines_and_source(mini_docs, mini_glossary):
    kb = KnowledgeBase(mini_docs, "ordbro", glossary=mini_glossary)
    answer = Answerer(kb, abstain_below=0.05).answer("irregular past tense of gå")
    assert not answer.abstained
    assert answer.source["doc_id"] == "datid"
    assert any("gik" in line for line in answer.lines)


def test_answerer_abstains_when_evidence_is_weak(mini_docs, mini_glossary):
    kb = KnowledgeBase(mini_docs, "ordbro", glossary=mini_glossary)
    answer = Answerer(kb, abstain_below=0.2).answer("photosynthesis in chloroplasts")
    assert answer.abstained
    assert answer.lines == []


def test_unknown_preset_raises():
    with pytest.raises(ValueError):
        get_preset("does-not-exist")
