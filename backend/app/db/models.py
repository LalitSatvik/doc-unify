"""SQLAlchemy ORM models. Tables are added alongside the plan phase that
needs them (see docs/plan.md); this module currently covers ingestion
(`Document`, `ContentBlockRow`).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings
from app.ingestion.base import BlockType


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class DocumentStatus(str, Enum):
    PENDING = "pending"
    INGESTED = "ingested"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(128))
    status: Mapped[DocumentStatus] = mapped_column(
        SqlEnum(DocumentStatus, name="document_status"), default=DocumentStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    blocks: Mapped[list[ContentBlockRow]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class ContentBlockRow(Base):
    """Persisted form of `app.ingestion.base.ContentBlock`."""

    __tablename__ = "content_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    page: Mapped[int] = mapped_column(Integer)
    block_type: Mapped[BlockType] = mapped_column(SqlEnum(BlockType, name="block_type"))
    text: Mapped[str | None] = mapped_column(default=None)
    table: Mapped[list[list[str]] | None] = mapped_column(JSON, default=None)
    bbox: Mapped[list[float] | None] = mapped_column(JSON, default=None)

    document: Mapped[Document] = relationship(back_populates="blocks")


class Chunk(Base):
    """An embedding-sized slice of a `ContentBlockRow`'s text, used for
    retrieval by both schema discovery and the chat agent."""

    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    content_block_id: Mapped[str] = mapped_column(ForeignKey("content_blocks.id"))
    page: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))


class SchemaFieldStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class SchemaField(Base):
    """One field in the unified schema -- proposed by discovery, then
    approved/renamed/rejected by the user before extraction runs."""

    __tablename__ = "schema_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(256))
    definition: Mapped[str] = mapped_column(String)
    status: Mapped[SchemaFieldStatus] = mapped_column(
        SqlEnum(SchemaFieldStatus, name="schema_field_status"),
        default=SchemaFieldStatus.PROPOSED,
    )
    has_conflict: Mapped[bool] = mapped_column(default=False)
    conflict_reason: Mapped[str | None] = mapped_column(default=None)
    member_labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TableCell(Base):
    """One (document, schema field) extracted value, with raw + normalized
    form, confidence, and provenance back to the exact source chunk."""

    __tablename__ = "table_cells"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    schema_field_id: Mapped[str] = mapped_column(ForeignKey("schema_fields.id"))
    raw_value: Mapped[str | None] = mapped_column(default=None)
    raw_unit: Mapped[str | None] = mapped_column(default=None)
    normalized_value: Mapped[float | None] = mapped_column(default=None)
    confidence: Mapped[float] = mapped_column(default=0.0)
    source_chunk_id: Mapped[str | None] = mapped_column(ForeignKey("chunks.id"), default=None)
    source_snippet: Mapped[str | None] = mapped_column(default=None)
    page: Mapped[int | None] = mapped_column(default=None)
    needs_review: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ReviewQueueItem(Base):
    """A `TableCell` that couldn't be mechanically normalized or was
    extracted with low confidence -- surfaced for human review rather
    than silently coerced or dropped."""

    __tablename__ = "review_queue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    table_cell_id: Mapped[str] = mapped_column(ForeignKey("table_cells.id"))
    reason: Mapped[str] = mapped_column(String)
    resolved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
