from fastapi.testclient import TestClient

from tests.ingestion.pdf_fixtures import make_text_pdf


def test_upload_ingests_and_persists_blocks(client: TestClient, tmp_path) -> None:
    pdf_path = tmp_path / "report.pdf"
    make_text_pdf(pdf_path, ["Revenue: $12,345"])

    with pdf_path.open("rb") as f:
        response = client.post(
            "/documents",
            files={"file": ("report.pdf", f, "application/pdf")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "report.pdf"
    assert body["status"] == "ingested"
    assert body["block_count"] == 1
    assert body["chunk_count"] == 1

    blocks_response = client.get(f"/documents/{body['id']}/blocks")
    assert blocks_response.status_code == 200
    blocks = blocks_response.json()
    assert len(blocks) == 1
    assert "Revenue" in blocks[0]["text"]


def test_upload_rejects_unsupported_format(client: TestClient, tmp_path) -> None:
    bad_path = tmp_path / "notes.xyz"
    bad_path.write_text("hello")

    with bad_path.open("rb") as f:
        response = client.post(
            "/documents",
            files={"file": ("notes.xyz", f, "application/octet-stream")},
        )

    assert response.status_code == 415


def test_list_documents(client: TestClient, tmp_path) -> None:
    pdf_path = tmp_path / "report.pdf"
    make_text_pdf(pdf_path, ["Revenue: $12,345"])
    with pdf_path.open("rb") as f:
        client.post("/documents", files={"file": ("report.pdf", f, "application/pdf")})

    response = client.get("/documents")

    assert response.status_code == 200
    documents = response.json()
    assert len(documents) == 1
    assert documents[0]["filename"] == "report.pdf"
