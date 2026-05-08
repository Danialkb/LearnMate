from __future__ import annotations

from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from services.documents.chunking import TextBlock, TextChunker
from services.documents.enums import DocumentFormat, DocumentLifecycleStatus
from services.documents.repositories import DocumentChunkCreateData, DocumentRepository
from services.documents.vector_index import (
    DocumentVectorIndex,
    EmbeddingClient,
    VectorPoint,
)


@dataclass(frozen=True, slots=True)
class IndexedDocument:
    document_id: UUID
    chunk_count: int
    vector_count: int


class DocumentIndexingService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: DocumentRepository,
        chunker: TextChunker,
        embeddings: EmbeddingClient,
        vector_index: DocumentVectorIndex,
    ) -> None:
        self._session = session
        self._repository = repository
        self._chunker = chunker
        self._embeddings = embeddings
        self._vector_index = vector_index

    async def index_text_blocks(
        self,
        *,
        document_id: UUID,
        source_id: UUID,
        title: str,
        document_format: DocumentFormat,
        text_blocks: list[TextBlock],
        language: str | None = None,
    ) -> IndexedDocument:
        await self._repository.update_lifecycle_status(
            document_id,
            DocumentLifecycleStatus.PROCESSING,
        )
        await self._session.flush()

        try:
            chunks = self._chunker.split(text_blocks)
            if not chunks:
                raise ValueError("No text chunks were produced")

            point_ids = [
                self._make_point_id(
                    document_id=document_id, chunk_index=chunk.chunk_index
                )
                for chunk in chunks
            ]
            vectors = await self._embeddings.embed_documents(
                [chunk.content for chunk in chunks]
            )
            if len(vectors) != len(chunks):
                raise ValueError("Embedding count does not match chunk count")

            await self._vector_index.ensure_collection()
            await self._vector_index.delete_document(str(document_id))

            await self._repository.replace_chunks(
                document_id,
                [
                    DocumentChunkCreateData(
                        source_id=source_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        vector_point_id=point_ids[index],
                    )
                    for index, chunk in enumerate(chunks)
                ],
            )

            await self._vector_index.upsert_points(
                [
                    VectorPoint(
                        point_id=point_ids[index],
                        vector=vector,
                        payload={
                            "document_id": str(document_id),
                            "source_id": str(source_id),
                            "chunk_index": chunk.chunk_index,
                            "title": title,
                            "format": document_format.value,
                            "language": language,
                            "page_start": chunk.page_start,
                            "page_end": chunk.page_end,
                            "text": chunk.content,
                        },
                    )
                    for index, (chunk, vector) in enumerate(
                        zip(chunks, vectors, strict=True)
                    )
                ]
            )

            await self._repository.update_lifecycle_status(
                document_id,
                DocumentLifecycleStatus.READY,
            )
            await self._session.commit()
            return IndexedDocument(
                document_id=document_id,
                chunk_count=len(chunks),
                vector_count=len(vectors),
            )
        except Exception:
            await self._session.rollback()
            await self._repository.update_lifecycle_status(
                document_id,
                DocumentLifecycleStatus.FAILED,
            )
            await self._session.commit()
            raise

    @staticmethod
    def _make_point_id(*, document_id: UUID, chunk_index: int) -> str:
        return str(uuid5(NAMESPACE_URL, f"learnmate:{document_id}:{chunk_index}"))
