from __future__ import annotations

from litestar.datastructures import State
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.repositories.documents import DocumentRepositoryImpl
from infrastructure.storage.s3 import S3Storage


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
