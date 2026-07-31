from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from ordbro.api import create_app
from ordbro.config import load_settings


@pytest.fixture
def client(tmp_path):
    settings = load_settings()
    settings.app = replace(settings.app, state_dir=str(tmp_path / "var"))
    return TestClient(create_app(settings))


def test_health_and_overview(client):
    assert client.get("/api/health").json()["status"] == "ok"
    overview = client.get("/api/overview").json()
    assert overview["skills"] == 18 and overview["llm"] == "none"
    assert overview["knowledge_base"]["documents"] >= 25


def test_practice_flow_with_two_attempts(client):
    data = client.post("/api/practice/next", json={"focus": "past_tense"}).json()
    exercise = data["exercise"]
    assert exercise["skill"] == "past_tense" and "answers" not in exercise
    first = client.post(
        "/api/practice/answer",
        json={"exercise_id": exercise["id"], "answer": "xxx", "attempt": 1},
    ).json()
    assert first["final"] is False and first["hint"]
    second = client.post(
        "/api/practice/answer",
        json={"exercise_id": exercise["id"], "answer": "xxx", "attempt": 2},
    ).json()
    assert second["final"] is True and second["answer"]
    assert second["source"]["doc_id"] in {"a2-datid", "weekenden"}
    learner = client.get("/api/learner").json()
    past = next(s for s in learner["skills"] if s["id"] == "past_tense")
    assert past["seen"] == 1 and past["correct"] == 0


def test_unknown_things_give_clear_errors(client):
    assert client.post("/api/practice/next", json={"focus": "nope"}).status_code == 404
    bad = client.post("/api/practice/answer", json={"exercise_id": "nope", "answer": "x"})
    assert bad.status_code == 404
    assert client.get("/api/learner", params={"learner": "../x"}).status_code == 422
    assert client.get("/api/notes/nope").status_code == 404


def test_ask_returns_source_and_word_cards(client):
    data = client.post("/api/ask", json={"question": "What is the plural of barn?"}).json()
    assert data["abstained"] is False
    assert data["source"]["doc_id"] == "a1-flertal"
    assert data["word_cards"][0]["da"] == "barn"
    assert [stage["stage"] for stage in data["trace"]["stages"]][0] == "analyze"


def test_write_check(client):
    data = client.post("/api/write/check", json={"text": "I dag jeg går i skole."}).json()
    assert data["issues"][0]["rule"] == "v2-inversion"
    assert data["issues"][0]["note"] == "a1-ordstilling"
    assert data["corrected"] == "I dag går jeg i skole."


def test_speak_assess_adds_note_text_to_tips(client):
    sentences = client.get("/api/speak/sentences").json()
    target = next(s for s in sentences if s["text"] == "Hvad hedder du?")
    data = client.post(
        "/api/speak/assess",
        json={"sentence_id": target["id"], "target": target["text"], "transcript": "vad heder du"},
    ).json()
    assert data["tips"][0]["id"] == "silent-h"
    assert "hv-" in data["tips"][0]["note"]


def test_feedback_and_summary(client):
    for _ in range(3):
        client.post(
            "/api/feedback",
            json={
                "kind": "exercise",
                "target_id": "neg-02",
                "helpful": False,
                "difficulty": "hard",
            },
        )
    summary = client.get("/api/feedback/summary").json()
    assert summary["total"] == 3
    assert summary["difficulty"]["negation"]["hard"] == 3
    assert any("negation" in s for s in summary["suggestions"])


def test_reset(client):
    client.post("/api/practice/answer", json={"exercise_id": "greet-01", "answer": "Godmorgen"})
    assert client.post("/api/learner/reset", json={}).json()["history"] == []
