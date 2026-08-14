"""Orchestrates extraction of an approved schema against a set of
documents: retrieve -> extract -> normalize -> persist, queuing anything
that can't be mechanically normalized or was extracted with low
confidence for human review instead of silently coercing it."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ReviewQueueItem
from app.db.models import SchemaField as SchemaFieldRow
from app.db.models import TableCell as TableCellRow
from app.embedding.retrieval import retrieve
from app.extraction.extract_field import extract_field
from app.extraction.normalize import normalize
from app.llm.base import LLMProvider

LOW_CONFIDENCE_THRESHOLD = 0.5
RETRIEVAL_TOP_K = 5


async def run_extraction(
    session: Session,
    llm_provider: LLMProvider,
    document_ids: list[str],
    schema_field_ids: list[str],
) -> list[TableCellRow]:
    fields = session.scalars(
        select(SchemaFieldRow).where(SchemaFieldRow.id.in_(schema_field_ids))
    ).all()

    cells: list[TableCellRow] = []
    for document_id in document_ids:
        for field in fields:
            chunks = await retrieve(
                session,
                llm_provider,
                f"{field.name}: {field.definition}",
                top_k=RETRIEVAL_TOP_K,
                document_ids=[document_id],
            )
            extracted = await extract_field(llm_provider, chunks, field.name, field.definition)
            if not extracted.found:
                continue

            needs_review = extracted.confidence < LOW_CONFIDENCE_THRESHOLD
            normalized_value = None
            if extracted.raw_value is not None:
                result = normalize(extracted.raw_value, extracted.raw_unit)
                normalized_value = result.normalized_value
                needs_review = needs_review or result.needs_review
                reason = result.reason
            else:
                reason = None

            cell = TableCellRow(
                document_id=document_id,
                schema_field_id=field.id,
                raw_value=extracted.raw_value,
                raw_unit=extracted.raw_unit,
                normalized_value=normalized_value,
                confidence=extracted.confidence,
                source_chunk_id=extracted.source_chunk_id,
                source_snippet=extracted.source_snippet,
                page=extracted.page,
                needs_review=needs_review,
            )
            session.add(cell)
            session.flush()
            cells.append(cell)

            if needs_review:
                session.add(
                    ReviewQueueItem(
                        table_cell_id=cell.id,
                        reason=reason or "low confidence extraction",
                    )
                )

    session.flush()
    return cells
