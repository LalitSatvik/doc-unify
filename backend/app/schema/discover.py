"""Orchestrates schema discovery end to end: candidate extraction per
chunk -> embedding + clustering across the whole set -> LLM cluster review
-> persisted `SchemaField` rows (status=proposed) for the user to approve."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk as ChunkRow
from app.db.models import SchemaField
from app.llm.base import LLMProvider
from app.schema.candidates import CandidateField, extract_candidates
from app.schema.clustering import cluster_candidates
from app.schema.review import review_cluster


async def discover_schema(
    session: Session, llm_provider: LLMProvider, document_ids: list[str]
) -> list[SchemaField]:
    chunks = session.scalars(
        select(ChunkRow).where(ChunkRow.document_id.in_(document_ids))
    ).all()

    candidates: list[CandidateField] = []
    for chunk in chunks:
        candidates.extend(
            await extract_candidates(llm_provider, chunk.document_id, chunk.page, chunk.text)
        )

    if not candidates:
        return []

    candidate_texts = [f"{c.label}: {c.definition or c.value}" for c in candidates]
    embeddings = await llm_provider.embed(candidate_texts)
    groups = cluster_candidates(candidates, embeddings)

    fields: list[SchemaField] = []
    for group in groups:
        members = [candidates[i] for i in group]
        review = await review_cluster(llm_provider, members)
        field = SchemaField(
            name=review.canonical_name,
            definition=review.definition,
            has_conflict=review.has_conflict,
            conflict_reason=review.conflict_reason,
            member_labels=review.member_labels,
        )
        session.add(field)
        fields.append(field)

    session.flush()
    return fields
