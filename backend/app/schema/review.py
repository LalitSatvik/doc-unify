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
        "definition that covers all of them.\n\n"
        f"Candidates:\n{listing}\n\n"
        "Before answering, check each label and definition for a qualifier "
        "that signals a different accounting basis, methodology, or period "
        "than the others -- for example: GAAP vs non-GAAP/adjusted/pro forma, "
        "gross vs net, before-tax vs after-tax, or a different quarter/year. "
        "Two labels can be worded completely differently and still be the "
        "same measurement (that's the normal case here) -- the deciding "
        "question is whether the *numbers* would differ for a reason other "
        "than wording. If you find such a qualifier on even one member, you "
        "MUST set has_conflict to true and name the specific qualifier in "
        "conflict_reason, even though the underlying metric name matches. "
        "Only set has_conflict to false when every member measures the exact "
        "same thing the exact same way."
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
