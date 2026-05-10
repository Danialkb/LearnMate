from __future__ import annotations

from datetime import datetime

from litestar.datastructures import UploadFile
from pydantic import BaseModel, ConfigDict

from services.documents.enums import (
    DocumentFormat,
    DocumentLifecycleStatus,
    DocumentSummaryStyle,
)


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


class DocumentSummaryRequest(BaseModel):
    style: DocumentSummaryStyle = DocumentSummaryStyle.BRIEF
    refresh: bool = False


class DocumentSummaryResponse(BaseModel):
    summary_id: str
    document_id: str
    style: DocumentSummaryStyle
    language: str | None
    content: str
    source_document_version: int
    cached: bool
    created_at: datetime
    updated_at: datetime
