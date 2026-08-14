"""Runs extraction against an approved schema, and exposes the result as
a unified table (with per-cell provenance), a review queue, and CSV
export."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ReviewQueueItem
from app.db.models import TableCell as TableCellRow
from app.db.session import get_session
from app.extraction.run import run_extraction
from app.extraction.table import build_unified_table, unified_table_to_csv
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


@router.get("/table")
async def get_table(session: Session = Depends(get_session)) -> list[dict]:
    return build_unified_table(session)


@router.get("/export.csv", response_class=PlainTextResponse)
async def export_csv(session: Session = Depends(get_session)) -> str:
    return unified_table_to_csv(build_unified_table(session))


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
