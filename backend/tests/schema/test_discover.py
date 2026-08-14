from sqlalchemy import select

from app.db.models import Chunk as ChunkRow
from app.db.models import SchemaField, SchemaFieldStatus
from app.db.repository import create_document
from app.llm.base import LLMResponse
from app.schema.discover import discover_schema
from tests.support.scripted_llm import ScriptedLLMProvider


async def _seed_chunk(session, document_id: str, page: int, text: str) -> None:
    session.add(ChunkRow(document_id=document_id, content_block_id="cb-1", page=page, text=text, embedding=[0.0, 0.0]))
    session.flush()


async def test_discover_schema_persists_one_field_per_cluster(session) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")
    await _seed_chunk(session, document.id, 1, "Total Revenue: $12,345K")
    await _seed_chunk(session, document.id, 2, "Net Sales: $12,400K")

    provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(
                raw_json={
                    "fields": [
                        {"label": "Total Revenue", "value": "12,345", "unit": "$K", "definition": "Revenue"}
                    ]
                }
            ),
            LLMResponse(
                raw_json={
                    "fields": [
                        {"label": "Net Sales", "value": "12,400", "unit": "$K", "definition": "Revenue"}
                    ]
                }
            ),
            LLMResponse(
                raw_json={
                    "canonical_name": "Total Revenue",
                    "definition": "Total revenue recognized in the period.",
                    "has_conflict": False,
                }
            ),
        ],
        # both candidate embeddings identical -> one cluster
        embed_fn=lambda texts: [[1.0, 0.0] for _ in texts],
    )

    fields = await discover_schema(session, provider, document_ids=[document.id])

    assert len(fields) == 1
    assert fields[0].name == "Total Revenue"
    assert fields[0].status == SchemaFieldStatus.PROPOSED
    assert fields[0].has_conflict is False
    assert sorted(fields[0].member_labels) == ["Net Sales", "Total Revenue"]

    persisted = session.scalars(select(SchemaField)).all()
    assert len(persisted) == 1


async def test_discover_schema_returns_empty_when_no_candidates_found(session) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")
    await _seed_chunk(session, document.id, 1, "Just narrative text.")

    provider = ScriptedLLMProvider(complete_responses=[LLMResponse(raw_json={"fields": []})])

    fields = await discover_schema(session, provider, document_ids=[document.id])

    assert fields == []
