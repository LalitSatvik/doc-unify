"""Runs extraction against an approved schema, and exposes the result as
a unified table (with per-cell provenance), a review queue, and CSV
export."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, ReviewQueueItem, SchemaField
from app.db.models import TableCell as TableCellRow
from app.db.session import get_session
from app.extraction.run import run_extraction
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider

router = APIRouter(prefix="/extraction", tags=["extraction"])


class RunRequest(BaseModel):
    document_ids: list[str]
    schema_field_ids: list[str]


class TableCellOut(BaseModel):
    id: str
    document_id: str
    schema_field_id: str
    raw_value: str | None
    raw_unit: str | None
    normalized_value: float | None
    confidence: float
    source_snippet: str | None
    page: int | None
    needs_review: bool

    model_config = {"from_attributes": True}


class ReviewQueueOut(BaseModel):
    id: str
    table_cell_id: str
    reason: str
    resolved: bool

    model_config = {"from_attributes": True}


class ReviewQueuePatch(BaseModel):
    resolved: bool


@router.post("/run", response_model=list[TableCellOut])
async def run(
    request: RunRequest,
    session: Session = Depends(get_session),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> list[TableCellRow]:
    cells = await run_extraction(
        session, llm_provider, request.document_ids, request.schema_field_ids
    )
    session.commit()
    return cells


def _build_unified_table(session: Session) -> list[dict]:
    documents = {d.id: d for d in session.scalars(select(Document)).all()}
    fields = {f.id: f for f in session.scalars(select(SchemaField)).all()}
    cells = session.scalars(select(TableCellRow)).all()

    rows: dict[str, dict] = {}
    for cell in cells:
        document = documents.get(cell.document_id)
        field = fields.get(cell.schema_field_id)
        if document is None or field is None:
            continue

        row = rows.setdefault(
            document.id,
            {"document_id": document.id, "document_filename": document.filename, "cells": {}},
        )
        row["cells"][field.name] = {
            "raw_value": cell.raw_value,
            "raw_unit": cell.raw_unit,
            "normalized_value": cell.normalized_value,
            "confidence": cell.confidence,
            "needs_review": cell.needs_review,
            "page": cell.page,
            "source_snippet": cell.source_snippet,
        }

    return list(rows.values())


@router.get("/table")
async def get_table(session: Session = Depends(get_session)) -> list[dict]:
    return _build_unified_table(session)


@router.get("/export.csv", response_class=PlainTextResponse)
async def export_csv(session: Session = Depends(get_session)) -> str:
    table = _build_unified_table(session)
    field_names = sorted({name for row in table for name in row["cells"]})

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["document", *field_names])
    for row in table:
        writer.writerow(
            [row["document_filename"]]
            + [
                row["cells"].get(name, {}).get("normalized_value", "")
                if row["cells"].get(name)
                else ""
                for name in field_names
            ]
        )
    return buffer.getvalue()


@router.get("/review-queue", response_model=list[ReviewQueueOut])
async def list_review_queue(session: Session = Depends(get_session)) -> list[ReviewQueueItem]:
    return list(session.scalars(select(ReviewQueueItem)).all())


@router.patch("/review-queue/{item_id}", response_model=ReviewQueueOut)
async def resolve_review_item(
    item_id: str, patch: ReviewQueuePatch, session: Session = Depends(get_session)
) -> ReviewQueueItem:
    item = session.get(ReviewQueueItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Review queue item not found")
    item.resolved = patch.resolved
    session.commit()
    return item
