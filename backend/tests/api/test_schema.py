from fastapi.testclient import TestClient

from app.llm.base import LLMResponse
from app.llm.factory import get_llm_provider
from app.main import app
from tests.ingestion.pdf_fixtures import make_text_pdf
from tests.support.scripted_llm import ScriptedLLMProvider


def json_response(data: dict) -> LLMResponse:
    return LLMResponse(raw_json=data)


def _upload(client: TestClient, tmp_path, name: str, text: str) -> str:
    path = tmp_path / name
    make_text_pdf(path, [text])
    with path.open("rb") as f:
        response = client.post("/documents", files={"file": (name, f, "application/pdf")})
    return response.json()["id"]


def test_discover_then_list_then_approve(client: TestClient, tmp_path) -> None:
    document_id = _upload(client, tmp_path, "report.pdf", "Total Revenue: $12,345K")

    provider = ScriptedLLMProvider(
        complete_responses=[
            json_response({"fields": [{"label": "Total Revenue", "value": "12,345", "unit": "$K"}]}),
            json_response(
                {
                    "canonical_name": "Total Revenue",
                    "definition": "Total revenue recognized in the period.",
                    "has_conflict": False,
                }
            ),
        ],
        embed_fn=lambda texts: [[1.0, 0.0] for _ in texts],
    )
    app.dependency_overrides[get_llm_provider] = lambda: provider

    discover_response = client.post("/schema/discover", json={"document_ids": [document_id]})
    assert discover_response.status_code == 200
    fields = discover_response.json()
    assert len(fields) == 1
    assert fields[0]["name"] == "Total Revenue"
    assert fields[0]["status"] == "proposed"
    field_id = fields[0]["id"]

    list_response = client.get("/schema/fields")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    patch_response = client.patch(f"/schema/fields/{field_id}", json={"status": "approved"})
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "approved"

    rename_response = client.patch(f"/schema/fields/{field_id}", json={"name": "Revenue"})
    assert rename_response.status_code == 200
    assert rename_response.json()["name"] == "Revenue"


def test_patch_unknown_field_returns_404(client: TestClient) -> None:
    response = client.patch("/schema/fields/does-not-exist", json={"status": "approved"})
    assert response.status_code == 404
