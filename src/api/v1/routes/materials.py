from __future__ import annotations

from uuid import UUID

from litestar import Request, Router, post
from litestar.datastructures import UploadFile
from litestar.di import Provide
from litestar.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.documents import (
    get_document_repository,
    get_document_vector_index,
    get_embedding_client,
    get_s3_storage,
    get_text_chunker,
    get_text_extractor,
)
from api.v1.schemas.documents import DocumentIndexResponse, DocumentUploadResponse
from infrastructure.db.repositories.documents import DocumentRepositoryImpl
from infrastructure.llm.embeddings import OpenAIEmbeddingClient
from infrastructure.logging import get_logger
from infrastructure.storage.s3 import S3Storage
from infrastructure.vector import QdrantDocumentVectorIndex
from services.documents.chunking import TextChunker
from services.documents.enums import DocumentLifecycleStatus
from services.documents.extraction import DocumentTextExtractor
from services.documents.indexing import DocumentIndexingService
from services.documents.upload import DocumentUploadService

logger = get_logger(__name__)


def _clean_form_value(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    raise HTTPException(status_code=400, detail="Invalid form field value")


@post("/upload", status_code=201)
async def upload_material(
    request: Request,
    session: AsyncSession,
    document_repository: DocumentRepositoryImpl,
    s3_storage: S3Storage,
    text_extractor: DocumentTextExtractor,
    text_chunker: TextChunker,
    embedding_client: OpenAIEmbeddingClient,
    document_vector_index: QdrantDocumentVectorIndex,
) -> DocumentUploadResponse:
    form = await request.form()
    uploaded_file = form.get("file")
    if not isinstance(uploaded_file, UploadFile):
        raise HTTPException(status_code=400, detail="File field 'file' is required")

    title = _clean_form_value(form.get("title"))
    description = _clean_form_value(form.get("description"))
    language = _clean_form_value(form.get("language"))

    try:
        file_data = await uploaded_file.read()
    finally:
        await uploaded_file.close()

    service = DocumentUploadService(
        session=session,
        repository=document_repository,
        storage=s3_storage,
    )

    logger.info("Uploading material filename=%s", uploaded_file.filename)
    result = await service.upload_file(
        data=file_data,
        filename=uploaded_file.filename,
        content_type=uploaded_file.content_type,
        title=title,
        description=description,
        language=language,
    )
    text_blocks = text_extractor.extract(
        data=file_data,
        document_format=result.document_format,
    )
    indexing_service = DocumentIndexingService(
        session=session,
        repository=document_repository,
        chunker=text_chunker,
        embeddings=embedding_client,
        vector_index=document_vector_index,
    )
    await indexing_service.index_text_blocks(
        document_id=result.document_id,
        source_id=result.source_id,
        title=result.title,
        document_format=result.document_format,
        language=language,
        text_blocks=text_blocks,
    )

    return DocumentUploadResponse(
        document_id=str(result.document_id),
        source_id=str(result.source_id),
        title=result.title,
        document_format=result.document_format,
        lifecycle_status=DocumentLifecycleStatus.READY,
        storage_key=result.storage_key,
        original_filename=result.original_filename,
    )


@post("/{document_id:uuid}/index", status_code=202)
async def index_material(
    document_id: UUID,
    session: AsyncSession,
    document_repository: DocumentRepositoryImpl,
    s3_storage: S3Storage,
    text_extractor: DocumentTextExtractor,
    text_chunker: TextChunker,
    embedding_client: OpenAIEmbeddingClient,
    document_vector_index: QdrantDocumentVectorIndex,
) -> DocumentIndexResponse:
    document = await document_repository.get_document_by_id(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.sources:
        raise HTTPException(status_code=400, detail="Document has no source")

    source = document.sources[0]
    if source.storage_key is None:
        raise HTTPException(status_code=400, detail="Document source is not in storage")

    file_data = await s3_storage.get_file(key=source.storage_key)
    text_blocks = text_extractor.extract(
        data=file_data,
        document_format=document.document_format,
    )
    service = DocumentIndexingService(
        session=session,
        repository=document_repository,
        chunker=text_chunker,
        embeddings=embedding_client,
        vector_index=document_vector_index,
    )
    result = await service.index_text_blocks(
        document_id=document.id,
        source_id=source.id,
        title=document.title,
        document_format=document.document_format,
        language=document.language,
        text_blocks=text_blocks,
    )
    return DocumentIndexResponse(
        document_id=str(result.document_id),
        chunk_count=result.chunk_count,
        vector_count=result.vector_count,
        lifecycle_status=document.lifecycle_status,
    )


materials_router = Router(
    path="/documents",
    dependencies={
        "document_repository": Provide(get_document_repository, sync_to_thread=False),
        "s3_storage": Provide(get_s3_storage, sync_to_thread=False),
        "text_extractor": Provide(get_text_extractor, sync_to_thread=False),
        "text_chunker": Provide(get_text_chunker, sync_to_thread=False),
        "embedding_client": Provide(get_embedding_client, sync_to_thread=False),
        "document_vector_index": Provide(
            get_document_vector_index,
            sync_to_thread=False,
        ),
    },
    route_handlers=[upload_material, index_material],
    tags=["Materials"],
)
