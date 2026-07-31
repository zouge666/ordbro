from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ordbro import __version__
from ordbro.api.schemas import (
    AnswerRequest,
    AskRequest,
    AssessRequest,
    CheckRequest,
    FeedbackRequest,
    NextRequest,
    ResetRequest,
)
from ordbro.config import Settings, load_settings
from ordbro.service import Ordbro
from ordbro.tutor.learner import utc_now


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    service = Ordbro(settings)
    app = FastAPI(title="Ordbro", version=__version__, docs_url="/api/docs", redoc_url=None)
    app.state.service = service

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": __version__, "preset": service.kb.preset.name}

    @app.get("/api/overview")
    def overview() -> dict[str, Any]:
        return service.overview()

    @app.get("/api/skills")
    def skills() -> list[dict[str, Any]]:
        return [
            {"id": s.id, "name": s.name, "name_da": s.name_da, "level": s.level, "about": s.about}
            for s in service.graph
        ]

    @app.get("/api/learner")
    def learner(learner: str = Query("local", pattern=r"^[a-z0-9_-]{1,40}$")) -> dict[str, Any]:
        with service.learner(learner) as state:
            return service.learner_summary(state)

    @app.post("/api/learner/reset")
    def reset(request: ResetRequest) -> dict[str, Any]:
        state = service.learners.reset(request.learner)
        return service.learner_summary(state)

    @app.post("/api/practice/next")
    def next_exercise(request: NextRequest) -> dict[str, Any]:
        if request.focus and request.focus != "review" and not service.graph.has(request.focus):
            raise HTTPException(404, f"unknown skill: {request.focus}")
        with service.learner(request.learner) as state:
            item, reason = service.engine.next(state, utc_now(), request.focus)
            if item is None:
                return {"exercise": None, "reason": reason}
            skill = service.graph.get(item.skill) if service.graph.has(item.skill) else None
            return {
                "exercise": item.public(),
                "reason": reason,
                "skill": None
                if skill is None
                else {
                    "id": skill.id,
                    "name": skill.name,
                    "name_da": skill.name_da,
                    "mastery": round(service.policy.mastery(state, skill.id), 3),
                },
            }

    @app.post("/api/practice/answer")
    def answer(request: AnswerRequest) -> dict[str, Any]:
        if request.exercise_id not in service.engine.items:
            raise HTTPException(404, f"unknown exercise: {request.exercise_id}")
        with service.learner(request.learner) as state:
            feedback = service.engine.answer(
                state, request.exercise_id, request.answer, request.attempt, utc_now()
            )
            return feedback.to_dict()

    @app.post("/api/ask")
    def ask(request: AskRequest) -> dict[str, Any]:
        return service.ask(request.question, request.top_k)

    @app.get("/api/notes/{doc_id}")
    def note(doc_id: str) -> dict[str, Any]:
        found = service.note(doc_id)
        if found is None:
            raise HTTPException(404, f"unknown note: {doc_id}")
        return found

    @app.post("/api/write/check")
    def check(request: CheckRequest) -> dict[str, Any]:
        return service.check_text(request.text)

    @app.get("/api/speak/sentences")
    def sentences() -> list[dict[str, Any]]:
        return service.sentences

    @app.post("/api/speak/assess")
    def speak(request: AssessRequest) -> dict[str, Any]:
        result = service.assess_speech(request.target, request.transcript)
        with service.learner(request.learner) as state:
            state.record(
                {
                    "ts": utc_now().isoformat(timespec="seconds"),
                    "exercise": request.sentence_id or "speak",
                    "skill": "",
                    "type": "speak",
                    "score": result["score"],
                    "final": True,
                }
            )
        return result

    @app.post("/api/feedback")
    def feedback(request: FeedbackRequest) -> dict[str, Any]:
        event = request.model_dump()
        item = service.engine.items.get(request.target_id)
        if item is not None:
            event["skill"] = item.skill
        return service.feedback.add(event)

    @app.get("/api/feedback/summary")
    def feedback_summary() -> dict[str, Any]:
        return service.feedback.summary()

    web = settings.web_path
    if (web / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=web / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(web / "index.html")

    return app
