from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, conlist


class QuizGenerationRequest(BaseModel):
    title: str | None = Field(
        default=None,
        description="Название материала, если оно известно.",
    )
    source_type: Literal["text", "article", "video"] = "text"
    content: str = Field(
        min_length=20,
        description="Текст конспекта, статьи или расшифровка видео.",
    )
    question_count: int = Field(default=5, ge=1, le=20)


class QuizQuestion(BaseModel):
    prompt: str
    options: conlist(str, min_length=2, max_length=5)
    correct_index: int = Field(ge=0)
    explanation: str
    source_hint: str | None = None


class QuizGenerationResponse(BaseModel):
    title: str
    summary: str
    key_points: list[str]
    questions: list[QuizQuestion]
    used_llm: bool
