import pytest

from app.ingestion.base import BlockType, ContentBlock


def test_text_block_holds_its_fields() -> None:
    block = ContentBlock(
        document_id="doc-1",
        page=1,
        block_type=BlockType.TEXT,
        text="Revenue: $12,345",
    )

    assert block.document_id == "doc-1"
    assert block.page == 1
    assert block.block_type == BlockType.TEXT
    assert block.text == "Revenue: $12,345"
    assert block.table is None
    assert block.bbox is None


def test_text_block_requires_non_empty_text() -> None:
    with pytest.raises(ValueError, match="text"):
        ContentBlock(document_id="doc-1", page=1, block_type=BlockType.TEXT, text="   ")


def test_table_block_requires_non_empty_table() -> None:
    with pytest.raises(ValueError, match="table"):
        ContentBlock(document_id="doc-1", page=1, block_type=BlockType.TABLE, table=[])


def test_table_block_holds_rows() -> None:
    block = ContentBlock(
        document_id="doc-1",
        page=2,
        block_type=BlockType.TABLE,
        table=[["Metric", "Value"], ["Revenue", "$12,345"]],
    )

    assert block.table == [["Metric", "Value"], ["Revenue", "$12,345"]]


def test_page_must_be_positive() -> None:
    with pytest.raises(ValueError, match="page"):
        ContentBlock(document_id="doc-1", page=0, block_type=BlockType.TEXT, text="x")
