from sqlalchemy import select

from app.db.models import ReviewQueueItem, SchemaField
from app.db.models import TableCell as TableCellRow
from app.db.repository import create_document
from app.extraction.run import run_extraction
from app.llm.base import LLMResponse
from tests.support.scripted_llm import ScriptedLLMProvider


def _make_chunk(document_id: str):
    from app.db.models import Chunk as ChunkRow

    return ChunkRow(
        id="c1",
        document_id=document_id,
        content_block_id="cb-1",
        page=3,
        text="Total Revenue was $12,345K in the quarter.",
        embedding=[0.0],
    )


async def test_run_extraction_creates_table_cell_with_normalized_value(session, monkeypatch) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")
    field = SchemaField(name="Total Revenue", definition="Revenue", member_labels=[])
    session.add(field)
    session.flush()

    chunk = _make_chunk(document.id)
    monkeypatch.setattr("app.extraction.run.retrieve", lambda *a, **k: _async_return([chunk]))

    provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(
                raw_json={
                    "found": True,
                    "raw_value": "12,345",
                    "raw_unit": "$K",
                    "confidence": 0.9,
                    "source_snippet": "Total Revenue was $12,345K in the quarter.",
                }
            )
        ]
    )

    cells = await run_extraction(session, provider, [document.id], [field.id])

    assert len(cells) == 1
    cell = cells[0]
    assert cell.raw_value == "12,345"
    assert cell.normalized_value == 12_345_000.0
    assert cell.needs_review is False
    assert cell.source_chunk_id == "c1"
    assert cell.page == 3

    persisted = session.scalars(select(TableCellRow)).all()
    assert len(persisted) == 1


async def test_run_extraction_queues_review_for_unrecognized_unit(session, monkeypatch) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")
    field = SchemaField(name="Headcount", definition="Employees", member_labels=[])
    session.add(field)
    session.flush()

    chunk = _make_chunk(document.id)
    monkeypatch.setattr("app.extraction.run.retrieve", lambda *a, **k: _async_return([chunk]))

    provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(
                raw_json={
                    "found": True,
                    "raw_value": "500",
                    "raw_unit": "widgets",
                    "confidence": 0.9,
                    "source_snippet": "Total Revenue was $12,345K in the quarter.",
                }
            )
        ]
    )

    cells = await run_extraction(session, provider, [document.id], [field.id])

    assert cells[0].needs_review is True
    queue_items = session.scalars(select(ReviewQueueItem)).all()
    assert len(queue_items) == 1
    assert queue_items[0].table_cell_id == cells[0].id


async def test_run_extraction_skips_when_field_not_found(session, monkeypatch) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")
    field = SchemaField(name="Headcount", definition="Employees", member_labels=[])
    session.add(field)
    session.flush()

    chunk = _make_chunk(document.id)
    monkeypatch.setattr("app.extraction.run.retrieve", lambda *a, **k: _async_return([chunk]))

    provider = ScriptedLLMProvider(complete_responses=[LLMResponse(raw_json={"found": False})])

    cells = await run_extraction(session, provider, [document.id], [field.id])

    assert cells == []


async def _async_return(value):
    return value
