from __future__ import annotations

from litestar import Request, Router, post
from litestar.datastructures import UploadFile
from litestar.di import Provide
from litestar.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.documents import get_document_repository, get_s3_storage
from api.v1.schemas.documents import DocumentUploadResponse
from infrastructure.db.repositories.documents import DocumentRepositoryImpl
from infrastructure.logging import get_logger
from infrastructure.storage.s3 import S3Storage
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

    return DocumentUploadResponse(
        document_id=str(result.document_id),
        source_id=str(result.source_id),
        title=result.title,
        document_format=result.document_format,
        lifecycle_status=result.lifecycle_status,
        storage_key=result.storage_key,
        original_filename=result.original_filename,
    )


materials_router = Router(
    path="/documents",
    dependencies={
        "document_repository": Provide(get_document_repository, sync_to_thread=False),
        "s3_storage": Provide(get_s3_storage, sync_to_thread=False),
    },
    route_handlers=[upload_material],
    tags=["Materials"],
)
