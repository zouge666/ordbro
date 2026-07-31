import io
import json

import pytest

from ordbro import llm
from ordbro.config import LLMSettings
from ordbro.rag import Answerer, KnowledgeBase


def test_composer_is_off_by_default():
    assert llm.make_composer(LLMSettings()) is None


def test_composer_needs_url_and_model():
    with pytest.raises(ValueError):
        llm.make_composer(LLMSettings(provider="openai-compatible"))


def test_composer_sends_passages_and_falls_back_on_errors(monkeypatch, mini_docs, mini_glossary):
    sent = {}

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        sent["body"] = json.loads(request.data)
        reply = {"choices": [{"message": {"content": "Use datid [1]."}}]}
        return Response(json.dumps(reply).encode())

    monkeypatch.setattr(llm, "urlopen", fake_urlopen)
    settings = LLMSettings(provider="openai-compatible", model="m", base_url="http://x/v1")
    kb = KnowledgeBase(mini_docs, "ordbro", glossary=mini_glossary)
    answer = Answerer(kb, abstain_below=0.05, composer=llm.make_composer(settings)).answer(
        "irregular past tense of gå"
    )
    assert answer.mode == "llm" and answer.text == "Use datid [1]."
    assert "Course notes" in sent["body"]["messages"][1]["content"]

    def broken(request, timeout):
        raise OSError("offline")

    monkeypatch.setattr(llm, "urlopen", broken)
    answer = Answerer(kb, abstain_below=0.05, composer=llm.make_composer(settings)).answer(
        "irregular past tense of gå"
    )
    assert answer.mode == "extractive" and answer.lines
