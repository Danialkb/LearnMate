from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.db.models.quiz import DocumentQuiz, QuizAttempt
from services.documents.enums import QuizGenerationMode
from services.documents.repositories import (
    DocumentQuizSaveData,
    QuizAttemptCreateData,
    QuizRepository,
)


class QuizRepositoryImpl(QuizRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_quiz_by_id(self, quiz_id: UUID) -> DocumentQuiz | None:
        statement = (
            select(DocumentQuiz)
            .where(DocumentQuiz.id == quiz_id)
            .options(selectinload(DocumentQuiz.attempts))
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_quiz(
        self,
        *,
        document_id: UUID | None,
        generation_mode: QuizGenerationMode,
        source_document_version: int | None,
    ) -> DocumentQuiz | None:
        statement = (
            select(DocumentQuiz)
            .where(
                DocumentQuiz.document_id == document_id,
                DocumentQuiz.generation_mode == generation_mode,
                DocumentQuiz.source_document_version == source_document_version,
            )
            .options(selectinload(DocumentQuiz.attempts))
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_document_quizzes(self, document_id: UUID) -> list[DocumentQuiz]:
        statement = (
            select(DocumentQuiz)
            .where(DocumentQuiz.document_id == document_id)
            .order_by(DocumentQuiz.created_at.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def save_quiz(self, data: DocumentQuizSaveData) -> DocumentQuiz:
        statement = (
            select(DocumentQuiz)
            .where(
                DocumentQuiz.document_id == data.document_id,
                DocumentQuiz.generation_mode == data.generation_mode,
                DocumentQuiz.source_document_version == data.source_document_version,
            )
            .with_for_update()
        )
        result = await self._session.execute(statement)
        quiz = result.scalar_one_or_none()

        if quiz is None:
            quiz = DocumentQuiz(
                document_id=data.document_id,
                title=data.title,
                query=data.query,
                generation_mode=data.generation_mode,
                language=data.language,
                question_count=data.question_count,
                payload=dict(data.payload),
                source_payload=[dict(item) for item in data.source_payload],
                prompt_version=data.prompt_version,
                source_document_version=data.source_document_version,
            )
            self._session.add(quiz)
        else:
            quiz.title = data.title
            quiz.query = data.query
            quiz.language = data.language
            quiz.question_count = data.question_count
            quiz.payload = dict(data.payload)
            quiz.source_payload = [dict(item) for item in data.source_payload]
            quiz.prompt_version = data.prompt_version

        await self._session.flush()
        return quiz

    async def create_attempt(self, data: QuizAttemptCreateData) -> QuizAttempt:
        attempt = QuizAttempt(
            quiz_id=data.quiz_id,
            document_id=data.document_id,
            answers=[dict(item) for item in data.answers],
            score=data.score,
            max_score=data.max_score,
            result_payload=[dict(item) for item in data.result_payload],
        )
        self._session.add(attempt)
        await self._session.flush()
        return attempt

    async def list_quiz_attempts(self, quiz_id: UUID) -> list[QuizAttempt]:
        statement = (
            select(QuizAttempt)
            .where(QuizAttempt.quiz_id == quiz_id)
            .order_by(QuizAttempt.created_at.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
