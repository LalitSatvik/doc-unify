"""Splits content blocks into embedding-sized `Chunk`s, preserving the
document/page/block provenance every chunk needs for citation later.

Accepts anything with `document_id`/`page`/`block_type`/`text`/`table`
attributes — both `app.ingestion.base.ContentBlock` (pre-persistence) and
`app.db.models.ContentBlockRow` (post-persistence, which also carries an
`id` that gets copied into `Chunk.content_block_id`) satisfy this.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.ingestion.base import BlockType

DEFAULT_MAX_CHARS = 1000
DEFAULT_OVERLAP = 150


class _Block(Protocol):
    document_id: str
    page: int
    block_type: BlockType
    text: str | None
    table: list[list[str]] | None


@dataclass
class Chunk:
    document_id: str
    page: int
    text: str
    content_block_id: str | None = None


def chunk_blocks(
    blocks: list[_Block],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for block in blocks:
        text = _block_to_text(block)
        for piece in _split_on_word_boundaries(text, max_chars, overlap):
            chunks.append(
                Chunk(
                    document_id=block.document_id,
                    page=block.page,
                    text=piece,
                    content_block_id=getattr(block, "id", None),
                )
            )
    return chunks


def _block_to_text(block: _Block) -> str:
    if block.block_type is BlockType.TABLE:
        assert block.table is not None
        return "\n".join(" | ".join(row) for row in block.table)
    assert block.text is not None
    return block.text


def _split_on_word_boundaries(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        pieces.append(text[start:end].strip())

        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return [p for p in pieces if p]
