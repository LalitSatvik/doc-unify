from app.embedding.chunking import chunk_blocks
from app.ingestion.base import BlockType, ContentBlock


def test_short_text_block_becomes_one_chunk() -> None:
    block = ContentBlock(document_id="doc-1", page=1, block_type=BlockType.TEXT, text="Revenue: $12,345")

    chunks = chunk_blocks([block])

    assert len(chunks) == 1
    assert chunks[0].text == "Revenue: $12,345"
    assert chunks[0].document_id == "doc-1"
    assert chunks[0].page == 1


def test_long_text_block_splits_on_word_boundaries_with_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(300))
    block = ContentBlock(document_id="doc-1", page=1, block_type=BlockType.TEXT, text=text)

    chunks = chunk_blocks([block], max_chars=200, overlap=50)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 200
        assert not chunk.text.startswith(" ")
        assert not chunk.text.endswith(" ")
    # overlap: the tail of one chunk should reappear at the head of the next
    assert chunks[0].text.split()[-1] in chunks[1].text.split()


def test_table_block_becomes_one_readable_chunk() -> None:
    block = ContentBlock(
        document_id="doc-1",
        page=2,
        block_type=BlockType.TABLE,
        table=[["Metric", "Value"], ["Revenue", "12345"]],
    )

    chunks = chunk_blocks([block])

    assert len(chunks) == 1
    assert "Metric" in chunks[0].text
    assert "Revenue" in chunks[0].text
    assert "12345" in chunks[0].text
    assert chunks[0].page == 2


def test_chunks_preserve_block_order_across_multiple_blocks() -> None:
    blocks = [
        ContentBlock(document_id="doc-1", page=1, block_type=BlockType.TEXT, text="first"),
        ContentBlock(document_id="doc-1", page=2, block_type=BlockType.TEXT, text="second"),
    ]

    chunks = chunk_blocks(blocks)

    assert [c.text for c in chunks] == ["first", "second"]
