from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LearnerId = Field("local", pattern=r"^[a-z0-9_-]{1,40}$")


class NextRequest(BaseModel):
    learner: str = LearnerId
    focus: str | None = Field(None, max_length=40)


class AnswerRequest(BaseModel):
    learner: str = LearnerId
    exercise_id: str = Field(..., max_length=120)
    answer: str = Field("", max_length=500)
    attempt: int = Field(1, ge=1, le=2)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=300)
    top_k: int = Field(5, ge=1, le=10)


class CheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class AssessRequest(BaseModel):
    learner: str = LearnerId
    sentence_id: str | None = Field(None, max_length=40)
    target: str = Field(..., min_length=1, max_length=300)
    transcript: str = Field("", max_length=500)
    alternatives: list[str] = Field(default_factory=list, max_length=5)


class FeedbackRequest(BaseModel):
    learner: str = LearnerId
    kind: Literal["exercise", "ask", "grammar", "speech"]
    target_id: str = Field(..., max_length=300)
    helpful: bool | None = None
    difficulty: Literal["easy", "ok", "hard"] | None = None
    comment: str = Field("", max_length=500)


class ResetRequest(BaseModel):
    learner: str = LearnerId
