from __future__ import annotations

from litestar.datastructures import UploadFile
from pydantic import BaseModel, ConfigDict

from services.documents.enums import DocumentFormat, DocumentLifecycleStatus


class DocumentUploadForm(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file: UploadFile
    title: str | None = None
    description: str | None = None
    language: str | None = None


class DocumentUploadResponse(BaseModel):
    document_id: str
    source_id: str
    title: str
    document_format: DocumentFormat
    lifecycle_status: DocumentLifecycleStatus
    storage_key: str
    original_filename: str


class DocumentIndexResponse(BaseModel):
    document_id: str
    chunk_count: int
    vector_count: int
    lifecycle_status: DocumentLifecycleStatus
