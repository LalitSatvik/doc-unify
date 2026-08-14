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
