"""LLM review of one cluster of candidate fields: proposes a canonical
name + definition, and explicitly flags clusters that look like they
conflate two different measurement methodologies instead of silently
merging them."""

from __future__ import annotations

from dataclasses import dataclass

from app.llm.base import LLMProvider
from app.schema.candidates import CandidateField

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "canonical_name": {"type": "string"},
        "definition": {"type": "string"},
        "has_conflict": {"type": "boolean"},
        "conflict_reason": {"type": "string"},
    },
    "required": ["canonical_name", "definition", "has_conflict"],
}


@dataclass
class ClusterReview:
    canonical_name: str
    definition: str
    has_conflict: bool
    conflict_reason: str | None
    member_labels: list[str]


async def review_cluster(llm_provider: LLMProvider, members: list[CandidateField]) -> ClusterReview:
    listing = "\n".join(
        f'- "{m.label}" = {m.value} {m.unit or ""} (doc {m.document_id}, p{m.page}): '
        f"{m.definition or 'no definition given'}"
        for m in members
    )
    prompt = (
        "These candidate fields were grouped as likely referring to the same "
        "underlying measurement. Propose ONE canonical field name and a short "
        "definition that covers all of them. If any member looks like it "
        "measures something meaningfully different (e.g. GAAP vs non-GAAP, "
        "gross vs net, a different time period or methodology) rather than "
        "just a differently-worded label for the same thing, set has_conflict "
        "true and explain why in conflict_reason -- never silently merge "
        "different measurements.\n\n"
        f"Candidates:\n{listing}"
    )
    response = await llm_provider.complete(
        [{"role": "user", "content": prompt}], json_schema=REVIEW_SCHEMA
    )
    data = response.raw_json or {}
    return ClusterReview(
        canonical_name=data.get("canonical_name") or members[0].label,
        definition=data.get("definition", ""),
        has_conflict=bool(data.get("has_conflict", False)),
        conflict_reason=data.get("conflict_reason") or None,
        member_labels=[m.label for m in members],
    )
