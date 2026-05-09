from __future__ import annotations

from litestar.datastructures import State
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.repositories.documents import DocumentRepositoryImpl
from infrastructure.llm.embeddings import OpenAIEmbeddingClient
from infrastructure.storage.s3 import S3Storage
from infrastructure.vector import QdrantDocumentVectorIndex
from services.documents.chunking import TextChunker
from services.documents.extraction import DocumentTextExtractor


def get_s3_storage(state: State) -> S3Storage:
    s3_storage: S3Storage | None = getattr(state, "s3_storage", None)
    if s3_storage is not None:
        return s3_storage

    settings = getattr(state, "settings", None)
    if settings is None:
        raise RuntimeError("Application settings are not configured")

    s3_storage = S3Storage(settings)
    state.s3_storage = s3_storage
    return s3_storage


def get_document_repository(session: AsyncSession) -> DocumentRepositoryImpl:
    return DocumentRepositoryImpl(session)


def get_text_extractor() -> DocumentTextExtractor:
    return DocumentTextExtractor()


def get_text_chunker() -> TextChunker:
    return TextChunker()


def get_embedding_client(state: State) -> OpenAIEmbeddingClient:
    embedding_client: OpenAIEmbeddingClient | None = getattr(
        state,
        "embedding_client",
        None,
    )
    if embedding_client is not None:
        return embedding_client

    settings = getattr(state, "settings", None)
    if settings is None:
        raise RuntimeError("Application settings are not configured")

    embedding_client = OpenAIEmbeddingClient(settings)
    state.embedding_client = embedding_client
    return embedding_client


def get_document_vector_index(state: State) -> QdrantDocumentVectorIndex:
    vector_index: QdrantDocumentVectorIndex | None = getattr(
        state,
        "document_vector_index",
        None,
    )
    if vector_index is not None:
        return vector_index

    settings = getattr(state, "settings", None)
    if settings is None:
        raise RuntimeError("Application settings are not configured")

    vector_index = QdrantDocumentVectorIndex(settings)
    state.document_vector_index = vector_index
    return vector_index
