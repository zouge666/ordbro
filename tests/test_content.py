from ordbro.config import load_settings
from ordbro.content import load_content
from ordbro.rag import Answerer, KnowledgeBase


def content():
    return load_content(load_settings().data_path)


def test_all_documents_have_front_matter_and_sections():
    docs = content().documents
    assert len(docs) >= 25
    for doc in docs:
        assert doc.metadata["kind"] in {"note", "dialogue"}
        assert doc.metadata["level"] in {"A1", "A2"}
        assert len(doc.sections) >= 2, doc.id


def test_vocabulary_has_complete_forms():
    vocab = content().vocab
    nouns = [e for e in vocab if e.pos == "noun"]
    verbs = [e for e in vocab if e.pos == "verb"]
    assert len(nouns) > 60 and len(verbs) > 40
    assert all(n.gender in {"en", "et"} and n.definite for n in nouns)
    assert all(v.present and v.past and v.perfect and v.aux in {"har", "er"} for v in verbs)


def test_lexicon_lookups():
    lexicon = content().lexicon
    entry, kind = lexicon.noun("børnene")
    assert entry.da == "barn" and kind == "plural_definite"
    assert lexicon.verb("gik")[0].da == "gå"
    assert lexicon.adjective("stort")[1] == "t_form"
    assert {e.pos for e, _ in lexicon.lookup("lærer")} == {"noun", "verb"}


def test_wrong_past_forms_point_to_the_real_form():
    lexicon = content().lexicon
    assert lexicon.wrong_past("gåede") == "gik"
    assert lexicon.wrong_past("spisede") == "spiste"
    assert lexicon.wrong_past("drikkede") == "drak"
    assert lexicon.wrong_past("lavede") is None


def test_knowledge_base_answers_from_the_real_corpus():
    data = content()
    kb = KnowledgeBase(data.documents, "ordbro", glossary=data.glossary)
    answerer = Answerer(kb)
    assert answerer.answer("What is the plural of barn?").source["doc_id"] == "a1-flertal"
    assert answerer.answer("Hvad betyder halv fire?").source["doc_id"] == "a1-klokken"
    assert answerer.answer("When do I use sin instead of hans?").source["doc_id"] == "a2-ejestedord"
