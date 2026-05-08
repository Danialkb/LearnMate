from __future__ import annotations

from pydantic import BaseModel

from services.documents.enums import DocumentFormat, DocumentLifecycleStatus


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
