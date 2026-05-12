from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from services.documents.enums import (
    DocumentFormat,
    DocumentLifecycleStatus,
    DocumentSourceType,
    DocumentSummaryStyle,
    QuizGenerationMode,
)

if TYPE_CHECKING:
    from infrastructure.db.models.document import (
        Document,
        DocumentChunk,
        DocumentSource,
        DocumentSummary,
    )
    from infrastructure.db.models.quiz import DocumentQuiz, QuizAttempt


@dataclass(frozen=True, slots=True)
class DocumentCreateData:
    title: str
    document_format: DocumentFormat
    description: str | None = None
    language: str | None = None
    lifecycle_status: DocumentLifecycleStatus = DocumentLifecycleStatus.NEW
    current_version: int = 1


@dataclass(frozen=True, slots=True)
class DocumentSourceCreateData:
    document_id: UUID
    source_kind: DocumentSourceType
    source_uri: str | None = None
    storage_key: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    content_hash: str | None = None
    payload: Mapping[str, object] | None = None
    retrieved_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DocumentChunkCreateData:
    chunk_index: int
    content: str
    source_id: UUID | None = None
    token_count: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    vector_point_id: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentSummarySaveData:
    document_id: UUID
    style: DocumentSummaryStyle
    language: str | None
    content: str
    prompt_version: str
    source_document_version: int


@dataclass(frozen=True, slots=True)
class DocumentQuizSaveData:
    document_id: UUID | None
    title: str | None
    query: str | None
    generation_mode: QuizGenerationMode
    language: str | None
    question_count: int
    payload: Mapping[str, object]
    source_payload: Sequence[Mapping[str, object]]
    prompt_version: str
    source_document_version: int | None


@dataclass(frozen=True, slots=True)
class QuizAttemptCreateData:
    quiz_id: UUID
    document_id: UUID | None
    answers: Sequence[Mapping[str, object]]
    score: int
    max_score: int
    result_payload: Sequence[Mapping[str, object]]


class DocumentRepository(ABC):
    @abstractmethod
    async def create_document(self, data: DocumentCreateData) -> Document: ...

    @abstractmethod
    async def create_source(self, data: DocumentSourceCreateData) -> DocumentSource: ...

    @abstractmethod
    async def create_chunks(
        self,
        document_id: UUID,
        chunks: Sequence[DocumentChunkCreateData],
    ) -> list[DocumentChunk]: ...

    @abstractmethod
    async def replace_chunks(
        self,
        document_id: UUID,
        chunks: Sequence[DocumentChunkCreateData],
    ) -> list[DocumentChunk]: ...

    @abstractmethod
    async def get_document_by_id(self, document_id: UUID) -> Document | None: ...

    @abstractmethod
    async def update_lifecycle_status(
        self,
        document_id: UUID,
        lifecycle_status: DocumentLifecycleStatus,
    ) -> Document | None: ...

    @abstractmethod
    async def get_summary(
        self,
        *,
        document_id: UUID,
        style: DocumentSummaryStyle,
        source_document_version: int,
    ) -> DocumentSummary | None: ...

    @abstractmethod
    async def save_summary(self, data: DocumentSummarySaveData) -> DocumentSummary: ...


class QuizRepository(ABC):
    @abstractmethod
    async def get_quiz_by_id(self, quiz_id: UUID) -> DocumentQuiz | None: ...

    @abstractmethod
    async def get_quiz(
        self,
        *,
        document_id: UUID | None,
        generation_mode: QuizGenerationMode,
        source_document_version: int | None,
    ) -> DocumentQuiz | None: ...

    @abstractmethod
    async def list_document_quizzes(self, document_id: UUID) -> list[DocumentQuiz]: ...

    @abstractmethod
    async def save_quiz(self, data: DocumentQuizSaveData) -> DocumentQuiz: ...

    @abstractmethod
    async def create_attempt(self, data: QuizAttemptCreateData) -> QuizAttempt: ...

    @abstractmethod
    async def list_quiz_attempts(self, quiz_id: UUID) -> list[QuizAttempt]: ...
