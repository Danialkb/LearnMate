from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.db.models.document import (
    Document,
    DocumentChunk,
    DocumentSource,
    DocumentSummary,
)
from services.documents.enums import DocumentLifecycleStatus, DocumentSummaryStyle
from services.documents.repositories import (
    DocumentChunkCreateData,
    DocumentCreateData,
    DocumentRepository,
    DocumentSourceCreateData,
    DocumentSummarySaveData,
)


class DocumentRepositoryImpl(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_document(self, data: DocumentCreateData) -> Document:
        document = Document(
            title=data.title,
            description=data.description,
            document_format=data.document_format,
            language=data.language,
            lifecycle_status=data.lifecycle_status,
            current_version=data.current_version,
        )
        self._session.add(document)
        await self._session.flush()
        return document

    async def create_source(self, data: DocumentSourceCreateData) -> DocumentSource:
        source = DocumentSource(
            document_id=data.document_id,
            source_kind=data.source_kind,
            source_uri=data.source_uri,
            storage_key=data.storage_key,
            original_filename=data.original_filename,
            mime_type=data.mime_type,
            file_size=data.file_size,
            content_hash=data.content_hash,
            payload=dict(data.payload) if data.payload is not None else None,
            retrieved_at=data.retrieved_at,
        )
        self._session.add(source)
        await self._session.flush()
        return source

    async def create_chunks(
        self,
        document_id: UUID,
        chunks: Sequence[DocumentChunkCreateData],
    ) -> list[DocumentChunk]:
        chunk_models = [
            DocumentChunk(
                document_id=document_id,
                source_id=chunk.source_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                vector_point_id=chunk.vector_point_id,
            )
            for chunk in chunks
        ]
        self._session.add_all(chunk_models)
        await self._session.flush()
        return chunk_models

    async def replace_chunks(
        self,
        document_id: UUID,
        chunks: Sequence[DocumentChunkCreateData],
    ) -> list[DocumentChunk]:
        await self._session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await self._session.flush()
        return await self.create_chunks(document_id=document_id, chunks=chunks)

    async def get_document_by_id(self, document_id: UUID) -> Document | None:
        statement = (
            select(Document)
            .where(Document.id == document_id)
            .options(
                selectinload(Document.sources),
                selectinload(Document.chunks).selectinload(DocumentChunk.source),
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def update_lifecycle_status(
        self,
        document_id: UUID,
        lifecycle_status: DocumentLifecycleStatus,
    ) -> Document | None:
        statement = select(Document).where(Document.id == document_id).with_for_update()
        result = await self._session.execute(statement)
        document = result.scalar_one_or_none()
        if document is None:
            return None

        document.lifecycle_status = lifecycle_status
        await self._session.flush()
        return document

    async def get_summary(
        self,
        *,
        document_id: UUID,
        style: DocumentSummaryStyle,
        source_document_version: int,
    ) -> DocumentSummary | None:
        statement = select(DocumentSummary).where(
            DocumentSummary.document_id == document_id,
            DocumentSummary.style == style,
            DocumentSummary.source_document_version == source_document_version,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def save_summary(self, data: DocumentSummarySaveData) -> DocumentSummary:
        statement = (
            select(DocumentSummary)
            .where(
                DocumentSummary.document_id == data.document_id,
                DocumentSummary.style == data.style,
                DocumentSummary.source_document_version == data.source_document_version,
            )
            .with_for_update()
        )
        result = await self._session.execute(statement)
        summary = result.scalar_one_or_none()
        if summary is None:
            summary = DocumentSummary(
                document_id=data.document_id,
                style=data.style,
                language=data.language,
                content=data.content,
                prompt_version=data.prompt_version,
                source_document_version=data.source_document_version,
            )
            self._session.add(summary)
        else:
            summary.language = data.language
            summary.content = data.content
            summary.prompt_version = data.prompt_version

        await self._session.flush()
        return summary
