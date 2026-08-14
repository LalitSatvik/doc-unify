"""Embeds a document's content blocks and persists the resulting chunks."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Chunk as ChunkRow
from app.db.models import ContentBlockRow
from app.embedding.chunking import chunk_blocks
from app.llm.base import LLMProvider


async def embed_and_store(
    session: Session,
    llm_provider: LLMProvider,
    document_id: str,
    blocks: list[ContentBlockRow],
) -> list[ChunkRow]:
    chunks = chunk_blocks(blocks)
    if not chunks:
        return []

    vectors = await llm_provider.embed([c.text for c in chunks])

    rows = [
        ChunkRow(
            document_id=document_id,
            content_block_id=chunk.content_block_id,
            page=chunk.page,
            text=chunk.text,
            embedding=vector,
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    session.add_all(rows)
    session.flush()
    return rows
