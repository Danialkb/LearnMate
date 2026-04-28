from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.storage.s3 import S3Storage
from services.documents.enums import (
    DocumentFormat,
    DocumentLifecycleStatus,
    DocumentSourceType,
)
from services.documents.repositories import (
    DocumentCreateData,
    DocumentRepository,
    DocumentSourceCreateData,
)

logger = logging.getLogger(__name__)

_EXTENSION_FORMAT_MAP: dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".txt": DocumentFormat.TXT,
    ".md": DocumentFormat.MARKDOWN,
    ".markdown": DocumentFormat.MARKDOWN,
    ".html": DocumentFormat.WEB_PAGE,
    ".htm": DocumentFormat.WEB_PAGE,
}

_CONTENT_TYPE_FORMAT_MAP: dict[str, DocumentFormat] = {
    "application/pdf": DocumentFormat.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentFormat.DOCX,
    "text/plain": DocumentFormat.TXT,
    "text/markdown": DocumentFormat.MARKDOWN,
    "text/html": DocumentFormat.WEB_PAGE,
}


@dataclass(frozen=True, slots=True)
class UploadedMaterial:
    document_id: UUID
    source_id: UUID
    title: str
    document_format: DocumentFormat
    lifecycle_status: DocumentLifecycleStatus
    storage_key: str
    original_filename: str


def _normalize_filename(filename: str) -> str:
    return Path(filename).name.replace(" ", "_")


def _detect_document_format(filename: str, content_type: str | None) -> DocumentFormat:
    suffix = Path(filename).suffix.lower()
    if suffix in _EXTENSION_FORMAT_MAP:
        return _EXTENSION_FORMAT_MAP[suffix]

    if content_type is not None and content_type in _CONTENT_TYPE_FORMAT_MAP:
        return _CONTENT_TYPE_FORMAT_MAP[content_type]

    raise ValueError(f"Unsupported document type for file {filename!r}")


class DocumentUploadService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: DocumentRepository,
        storage: S3Storage,
    ) -> None:
        self._session = session
        self._repository = repository
        self._storage = storage

    async def upload_file(
        self,
        *,
        data: bytes,
        filename: str,
        content_type: str | None,
        title: str | None,
        description: str | None = None,
        language: str | None = None,
    ) -> UploadedMaterial:
        if not data:
            raise ValueError("Uploaded file is empty")

        original_filename = _normalize_filename(filename)
        document_format = _detect_document_format(original_filename, content_type)
        document_title = title.strip() if title else Path(original_filename).stem
        if not document_title:
            document_title = original_filename

        storage_key: str | None = None

        try:
            document = await self._repository.create_document(
                DocumentCreateData(
                    title=document_title,
                    description=description,
                    document_format=document_format,
                    language=language,
                    lifecycle_status=DocumentLifecycleStatus.NEW,
                )
            )
            storage_key = self._storage.generate_document_object_key(
                document_id=document.id,
                filename=original_filename,
            )

            upload_info = await self._storage.upload_file(
                key=storage_key,
                data=data,
                content_type=content_type,
            )

            source = await self._repository.create_source(
                DocumentSourceCreateData(
                    document_id=document.id,
                    source_kind=DocumentSourceType.LOCAL_FILE,
                    storage_key=upload_info.key,
                    original_filename=original_filename,
                    mime_type=content_type,
                    file_size=len(data),
                    content_hash=hashlib.sha256(data).hexdigest(),
                )
            )

            await self._session.commit()
            return UploadedMaterial(
                document_id=document.id,
                source_id=source.id,
                title=document.title,
                document_format=document.document_format,
                lifecycle_status=document.lifecycle_status,
                storage_key=upload_info.key,
                original_filename=original_filename,
            )
        except Exception:
            await self._session.rollback()

            if storage_key is not None:
                try:
                    await self._storage.delete_file(key=storage_key)
                except Exception:
                    logger.exception(
                        "Failed to delete uploaded file %s after error", storage_key
                    )

            raise
