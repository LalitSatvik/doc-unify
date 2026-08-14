"""Document upload/listing: runs ingestion synchronously and persists the
resulting content blocks. Ingestion is fast enough per-document (seconds)
that a background job isn't warranted yet; revisit if large batch uploads
become common.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ContentBlockRow, Document, DocumentStatus
from app.db.repository import create_document, mark_document_status, save_content_blocks
from app.db.session import get_session
from app.ingestion.registry import UnsupportedFormatError, get_extractor

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str
    status: DocumentStatus
    block_count: int

    model_config = {"from_attributes": True}


class ContentBlockOut(BaseModel):
    id: str
    page: int
    block_type: str
    text: str | None
    table: list[list[str]] | None
    bbox: list[float] | None

    model_config = {"from_attributes": True}


@router.post("", status_code=201, response_model=DocumentOut)
async def upload_document(
    file: UploadFile, session: Session = Depends(get_session)
) -> DocumentOut:
    suffix = Path(file.filename or "").suffix
    try:
        extractor = get_extractor(Path(file.filename or ""))
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    document = create_document(
        session,
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
    )

    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp.flush()

        try:
            blocks = extractor.extract(Path(tmp.name), document_id=document.id)
        except Exception:
            mark_document_status(session, document, DocumentStatus.FAILED)
            session.commit()
            raise

    rows = save_content_blocks(session, document.id, blocks)
    mark_document_status(session, document, DocumentStatus.INGESTED)
    session.commit()

    return DocumentOut(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        status=document.status,
        block_count=len(rows),
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(session: Session = Depends(get_session)) -> list[DocumentOut]:
    documents = session.scalars(select(Document)).all()
    return [
        DocumentOut(
            id=d.id,
            filename=d.filename,
            content_type=d.content_type,
            status=d.status,
            block_count=len(d.blocks),
        )
        for d in documents
    ]


@router.get("/{document_id}/blocks", response_model=list[ContentBlockOut])
async def list_document_blocks(
    document_id: str, session: Session = Depends(get_session)
) -> list[ContentBlockRow]:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    blocks = session.scalars(
        select(ContentBlockRow).where(ContentBlockRow.document_id == document_id)
    ).all()
    return blocks
