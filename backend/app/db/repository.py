"""Persistence helpers bridging in-memory ingestion output
(`app.ingestion.base.ContentBlock`) and the ORM."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import ContentBlockRow, Document, DocumentStatus
from app.ingestion.base import ContentBlock


def create_document(session: Session, filename: str, content_type: str) -> Document:
    document = Document(filename=filename, content_type=content_type)
    session.add(document)
    session.flush()
    return document


def save_content_blocks(
    session: Session, document_id: str, blocks: list[ContentBlock]
) -> list[ContentBlockRow]:
    rows = [
        ContentBlockRow(
            document_id=document_id,
            page=block.page,
            block_type=block.block_type,
            text=block.text,
            table=block.table,
            bbox=list(block.bbox) if block.bbox else None,
        )
        for block in blocks
    ]
    session.add_all(rows)
    session.flush()
    return rows


def mark_document_status(session: Session, document: Document, status: DocumentStatus) -> None:
    document.status = status
    session.flush()
