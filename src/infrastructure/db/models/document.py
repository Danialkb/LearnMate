import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    UUID,
    BigInteger,
    DateTime,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db import Base
from infrastructure.db.models.mixins import CreatedAtMixin, TimestampMixin, UUIDMixin
from services.documents.enums import (
    DocumentFormat,
    DocumentLifecycleStatus,
    DocumentSourceType,
)


class Document(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    document_format: Mapped[DocumentFormat] = mapped_column(
        SAEnum(DocumentFormat, name="document_format"),
        nullable=False,
    )
    language: Mapped[str | None] = mapped_column(String(20))

    lifecycle_status: Mapped[DocumentLifecycleStatus] = mapped_column(
        SAEnum(DocumentLifecycleStatus, name="document_lifecycle_status"),
        nullable=False,
        default=DocumentLifecycleStatus.NEW,
    )

    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    sources: Mapped[list["DocumentSource"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )


class DocumentSource(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "document_sources"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_kind: Mapped[DocumentSourceType] = mapped_column(
        SAEnum(DocumentSourceType, name="document_source_kind"),
        nullable=False,
    )

    source_uri: Mapped[str | None] = mapped_column(Text)
    storage_key: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int | None] = mapped_column(BigInteger)

    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped[Document] = relationship(back_populates="sources")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="source")


class DocumentChunk(UUIDMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_chunk_index",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_sources.id", ondelete="SET NULL"),
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)

    vector_point_id: Mapped[str | None] = mapped_column(String(255), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(back_populates="chunks")
    source: Mapped[DocumentSource | None] = relationship(back_populates="chunks")
