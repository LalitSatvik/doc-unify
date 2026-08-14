from sqlalchemy.orm import Session

from app.db.models import DocumentStatus
from app.db.repository import create_document, mark_document_status, save_content_blocks
from app.ingestion.base import BlockType, ContentBlock


def test_create_document_defaults_to_pending(session: Session) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")

    assert document.id
    assert document.filename == "report.pdf"
    assert document.status == DocumentStatus.PENDING


def test_save_content_blocks_persists_and_links_to_document(session: Session) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")
    blocks = [
        ContentBlock(document_id=document.id, page=1, block_type=BlockType.TEXT, text="Revenue"),
        ContentBlock(
            document_id=document.id,
            page=1,
            block_type=BlockType.TABLE,
            table=[["Metric", "Value"]],
        ),
    ]

    rows = save_content_blocks(session, document.id, blocks)

    assert len(rows) == 2
    assert rows[0].text == "Revenue"
    assert rows[1].table == [["Metric", "Value"]]
    assert all(row.document_id == document.id for row in rows)
    assert len(document.blocks) == 2


def test_mark_document_status_updates_status(session: Session) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")

    mark_document_status(session, document, DocumentStatus.INGESTED)

    assert document.status == DocumentStatus.INGESTED
