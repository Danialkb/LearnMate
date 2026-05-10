from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from litestar import Router, get, post
from litestar.di import Provide
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException
from litestar.params import Body
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.documents import (
    get_document_repository,
    get_document_vector_index,
    get_embedding_client,
    get_s3_storage,
    get_text_chunker,
    get_text_extractor,
)
from api.dependencies.llm import get_llm_factory
from api.v1.schemas.documents import (
    DocumentIndexResponse,
    DocumentSummaryRequest,
    DocumentSummaryResponse,
    DocumentUploadForm,
    DocumentUploadResponse,
)
from infrastructure.db.repositories.documents import DocumentRepositoryImpl
from infrastructure.llm.embeddings import OpenAIEmbeddingClient
from infrastructure.llm.openai import LLMFactory
from infrastructure.logging import get_logger
from infrastructure.storage.s3 import S3Storage
from infrastructure.vector import QdrantDocumentVectorIndex
from services.documents.chunking import TextChunker
from services.documents.enums import DocumentLifecycleStatus, DocumentSummaryStyle
from services.documents.extraction import DocumentTextExtractor
from services.documents.indexing import DocumentIndexingService
from services.documents.summary import (
    DocumentHasNoChunksError,
    DocumentNotFoundError,
    DocumentNotReadyError,
    DocumentSummaryNotFoundError,
    DocumentSummaryService,
)
from services.documents.upload import DocumentUploadService
from services.llm.enums import LLMUseCase

logger = get_logger(__name__)

if TYPE_CHECKING:
    from infrastructure.db.models.document import DocumentSummary


def _clean_form_value(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    raise HTTPException(status_code=400, detail="Invalid form field value")


@post("/upload", status_code=201)
async def upload_material(
    data: Annotated[
        DocumentUploadForm,
        Body(media_type=RequestEncodingType.MULTI_PART),
    ],
    session: AsyncSession,
    document_repository: DocumentRepositoryImpl,
    s3_storage: S3Storage,
    text_extractor: DocumentTextExtractor,
    text_chunker: TextChunker,
    embedding_client: OpenAIEmbeddingClient,
    document_vector_index: QdrantDocumentVectorIndex,
) -> DocumentUploadResponse:
    try:
        file_data = await data.file.read()
    finally:
        await data.file.close()

    service = DocumentUploadService(
        session=session,
        repository=document_repository,
        storage=s3_storage,
    )

    title = _clean_form_value(data.title)
    description = _clean_form_value(data.description)
    language = _clean_form_value(data.language)

    logger.info("Uploading material filename=%s", data.file.filename)
    result = await service.upload_file(
        data=file_data,
        filename=data.file.filename,
        content_type=data.file.content_type,
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


@post("/{document_id:uuid}/summary", status_code=200)
async def generate_document_summary(
    document_id: UUID,
    data: DocumentSummaryRequest,
    session: AsyncSession,
    document_repository: DocumentRepositoryImpl,
    llm_factory: LLMFactory,
) -> DocumentSummaryResponse:
    service = DocumentSummaryService(
        repository=document_repository,
        llm=llm_factory.create(LLMUseCase.SUMMARY),
    )
    try:
        result = await service.generate_summary(
            document_id=document_id,
            style=data.style,
            refresh=data.refresh,
        )
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    except DocumentNotReadyError:
        raise HTTPException(status_code=409, detail="Document is not ready")
    except DocumentHasNoChunksError:
        raise HTTPException(status_code=400, detail="Document has no chunks")

    if not result.cached:
        await session.commit()

    return _summary_response(result.summary, cached=result.cached)


@get("/{document_id:uuid}/summary")
async def get_document_summary(
    document_id: UUID,
    document_repository: DocumentRepositoryImpl,
    style: DocumentSummaryStyle = DocumentSummaryStyle.BRIEF,
) -> DocumentSummaryResponse:
    service = DocumentSummaryService(repository=document_repository)
    try:
        summary = await service.get_summary(document_id=document_id, style=style)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    except DocumentSummaryNotFoundError:
        raise HTTPException(status_code=404, detail="Document summary not found")

    return _summary_response(summary, cached=True)


def _summary_response(
    summary: DocumentSummary,
    *,
    cached: bool,
) -> DocumentSummaryResponse:
    return DocumentSummaryResponse(
        summary_id=str(summary.id),
        document_id=str(summary.document_id),
        style=summary.style,
        language=summary.language,
        content=summary.content,
        source_document_version=summary.source_document_version,
        cached=cached,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
    )


materials_router = Router(
    path="/documents",
    dependencies={
        "document_repository": Provide(get_document_repository, sync_to_thread=False),
        "llm_factory": Provide(get_llm_factory, sync_to_thread=False),
        "s3_storage": Provide(get_s3_storage, sync_to_thread=False),
        "text_extractor": Provide(get_text_extractor, sync_to_thread=False),
        "text_chunker": Provide(get_text_chunker, sync_to_thread=False),
        "embedding_client": Provide(get_embedding_client, sync_to_thread=False),
        "document_vector_index": Provide(
            get_document_vector_index,
            sync_to_thread=False,
        ),
    },
    route_handlers=[
        upload_material,
        index_material,
        generate_document_summary,
        get_document_summary,
    ],
    tags=["Materials"],
)
