"""Nearest-neighbor chunk retrieval over pgvector, shared by schema
discovery and the chat agent."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk as ChunkRow
from app.llm.base import LLMProvider


def similar_chunks_query(query_embedding: list[float], top_k: int = 5, document_ids: list[str] | None = None):
    stmt = select(ChunkRow).order_by(ChunkRow.embedding.cosine_distance(query_embedding)).limit(top_k)
    if document_ids:
        stmt = stmt.where(ChunkRow.document_id.in_(document_ids))
    return stmt


def retrieve_by_vector(
    session: Session,
    query_embedding: list[float],
    top_k: int = 5,
    document_ids: list[str] | None = None,
) -> list[ChunkRow]:
    stmt = similar_chunks_query(query_embedding, top_k=top_k, document_ids=document_ids)
    return list(session.scalars(stmt).all())


async def retrieve(
    session: Session,
    llm_provider: LLMProvider,
    query_text: str,
    top_k: int = 5,
    document_ids: list[str] | None = None,
) -> list[ChunkRow]:
    [query_embedding] = await llm_provider.embed([query_text])
    return retrieve_by_vector(session, query_embedding, top_k=top_k, document_ids=document_ids)
