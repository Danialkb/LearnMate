from __future__ import annotations

import typing
import uuid
from typing import Any

from sqlalchemy import JSON, UUID
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db import Base
from infrastructure.db.models.mixins import CreatedAtMixin, TimestampMixin, UUIDMixin
from services.documents.enums import QuizGenerationMode

if typing.TYPE_CHECKING:
    from infrastructure.db.models.document import Document


class DocumentQuiz(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_quizzes"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "source_document_version",
            "generation_mode",
            name="uq_document_quizzes_document_version_mode",
        ),
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255))
    query: Mapped[str | None] = mapped_column(Text)
    generation_mode: Mapped[QuizGenerationMode] = mapped_column(
        SAEnum(
            QuizGenerationMode,
            name="quiz_generation_mode",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    language: Mapped[str | None] = mapped_column(String(20))
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_payload: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source_document_version: Mapped[int | None] = mapped_column(Integer)

    document: Mapped[Document | None] = relationship(back_populates="quizzes")
    attempts: Mapped[list[QuizAttempt]] = relationship(
        back_populates="quiz",
        cascade="all, delete-orphan",
    )


class QuizAttempt(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "quiz_attempts"

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        index=True,
    )
    answers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    result_payload: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)

    quiz: Mapped[DocumentQuiz] = relationship(back_populates="attempts")
    document: Mapped[Document | None] = relationship()
