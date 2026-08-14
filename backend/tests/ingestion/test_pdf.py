from pathlib import Path

from app.ingestion.base import BlockType
from app.ingestion.pdf import PDFExtractor
from tests.ingestion.pdf_fixtures import make_scanned_pdf, make_table_pdf, make_text_pdf


def test_extracts_text_per_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "text.pdf"
    make_text_pdf(pdf_path, ["Revenue: $12,345", "Net Sales: $6,789"])

    blocks = PDFExtractor().extract(pdf_path, document_id="doc-1")

    text_blocks = [b for b in blocks if b.block_type == BlockType.TEXT]
    assert [b.page for b in text_blocks] == [1, 2]
    assert "Revenue" in text_blocks[0].text
    assert "Net Sales" in text_blocks[1].text
    assert all(b.document_id == "doc-1" for b in text_blocks)


def test_extracts_table_as_table_block(tmp_path: Path) -> None:
    pdf_path = tmp_path / "table.pdf"
    make_table_pdf(pdf_path, [["Metric", "Value"], ["Revenue", "12345"]])

    blocks = PDFExtractor().extract(pdf_path, document_id="doc-1")

    table_blocks = [b for b in blocks if b.block_type == BlockType.TABLE]
    assert len(table_blocks) == 1
    assert table_blocks[0].table == [["Metric", "Value"], ["Revenue", "12345"]]
    assert table_blocks[0].page == 1


def test_ocr_fallback_for_scanned_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    make_scanned_pdf(pdf_path, "Net Sales 98765")

    blocks = PDFExtractor().extract(pdf_path, document_id="doc-1")

    text_blocks = [b for b in blocks if b.block_type == BlockType.TEXT]
    assert len(text_blocks) == 1
    assert "Net Sales" in text_blocks[0].text
    assert "98765" in text_blocks[0].text
