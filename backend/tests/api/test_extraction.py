from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Chunk as ChunkRow
from app.llm.base import LLMResponse
from app.llm.factory import get_llm_provider
from app.main import app
from tests.ingestion.pdf_fixtures import make_text_pdf
from tests.support.scripted_llm import ScriptedLLMProvider


async def _fake_retrieve(session, llm_provider, query_text, top_k=5, document_ids=None):
    """Bypasses pgvector's cosine_distance operator (unsupported on the
    SQLite test backend) -- just returns every chunk for the requested
    documents, which is enough when a test seeds one chunk per document."""
    stmt = select(ChunkRow)
    if document_ids:
        stmt = stmt.where(ChunkRow.document_id.in_(document_ids))
    return list(session.scalars(stmt).all())


def _upload(client: TestClient, tmp_path, name: str, text: str) -> str:
    path = tmp_path / name
    make_text_pdf(path, [text])
    with path.open("rb") as f:
        response = client.post("/documents", files={"file": (name, f, "application/pdf")})
    return response.json()["id"]


def _discover_and_approve(client: TestClient, document_id: str) -> str:
    provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(raw_json={"fields": [{"label": "Total Revenue", "value": "12,345", "unit": "$K"}]}),
            LLMResponse(
                raw_json={
                    "canonical_name": "Total Revenue",
                    "definition": "Total revenue recognized in the period.",
                    "has_conflict": False,
                }
            ),
        ],
        embed_fn=lambda texts: [[1.0, 0.0] for _ in texts],
    )
    app.dependency_overrides[get_llm_provider] = lambda: provider
    fields = client.post("/schema/discover", json={"document_ids": [document_id]}).json()
    field_id = fields[0]["id"]
    client.patch(f"/schema/fields/{field_id}", json={"status": "approved"})
    return field_id


def test_run_extraction_then_view_unified_table(client: TestClient, tmp_path, monkeypatch) -> None:
    document_id = _upload(client, tmp_path, "report.pdf", "Total Revenue: $12,345K")
    field_id = _discover_and_approve(client, document_id)
    monkeypatch.setattr("app.extraction.run.retrieve", _fake_retrieve)

    extract_provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(
                raw_json={
                    "found": True,
                    "raw_value": "12,345",
                    "raw_unit": "$K",
                    "confidence": 0.9,
                    "source_snippet": "Total Revenue: $12,345K",
                }
            )
        ],
        embed_fn=lambda texts: [[1.0, 0.0] for _ in texts],
    )
    app.dependency_overrides[get_llm_provider] = lambda: extract_provider

    run_response = client.post(
        "/extraction/run", json={"document_ids": [document_id], "schema_field_ids": [field_id]}
    )
    assert run_response.status_code == 200
    cells = run_response.json()
    assert len(cells) == 1
    assert cells[0]["raw_value"] == "12,345"
    assert cells[0]["normalized_value"] == 12_345_000.0

    table_response = client.get("/extraction/table")
    assert table_response.status_code == 200
    table = table_response.json()
    assert len(table) == 1
    assert table[0]["document_filename"] == "report.pdf"
    assert table[0]["cells"]["Total Revenue"]["normalized_value"] == 12_345_000.0

    csv_response = client.get("/extraction/export.csv")
    assert csv_response.status_code == 200
    assert "Total Revenue" in csv_response.text
    assert "report.pdf" in csv_response.text


def test_review_queue_lists_and_resolves_flagged_cells(client: TestClient, tmp_path, monkeypatch) -> None:
    document_id = _upload(client, tmp_path, "report.pdf", "Headcount: 500 widgets")
    field_id = _discover_and_approve(client, document_id)
    monkeypatch.setattr("app.extraction.run.retrieve", _fake_retrieve)

    extract_provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(
                raw_json={
                    "found": True,
                    "raw_value": "500",
                    "raw_unit": "widgets",
                    "confidence": 0.9,
                    "source_snippet": "Headcount: 500 widgets",
                }
            )
        ],
        embed_fn=lambda texts: [[1.0, 0.0] for _ in texts],
    )
    app.dependency_overrides[get_llm_provider] = lambda: extract_provider

    client.post(
        "/extraction/run", json={"document_ids": [document_id], "schema_field_ids": [field_id]}
    )

    queue_response = client.get("/extraction/review-queue")
    assert queue_response.status_code == 200
    queue = queue_response.json()
    assert len(queue) == 1
    item_id = queue[0]["id"]
    assert queue[0]["resolved"] is False

    resolve_response = client.patch(f"/extraction/review-queue/{item_id}", json={"resolved": True})
    assert resolve_response.status_code == 200
    assert resolve_response.json()["resolved"] is True
