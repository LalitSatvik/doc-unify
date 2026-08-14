"""Per-chunk candidate-field extraction: label as written, value as
written, unit as written, and a short definition/context sentence -- the
raw material schema discovery clusters and reviews."""

from __future__ import annotations

from dataclasses import dataclass

from app.llm.base import LLMProvider

CANDIDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "unit": {"type": "string"},
                    "definition": {"type": "string"},
                },
                "required": ["label", "value"],
            },
        }
    },
    "required": ["fields"],
}

_SNIPPET_LENGTH = 280


@dataclass
class CandidateField:
    label: str
    value: str
    unit: str | None
    definition: str | None
    document_id: str
    page: int
    snippet: str


async def extract_candidates(
    llm_provider: LLMProvider, document_id: str, page: int, text: str
) -> list[CandidateField]:
    prompt = (
        "Extract every reportable data field (metric, KPI, financial figure) "
        "from the text below. For each, give: label (exactly as written), "
        "value (exactly as written), unit (as written, or empty string if "
        "none), and a short one-sentence definition or context. Return only "
        "fields with a concrete value -- skip narrative text with no "
        "extractable figure.\n\n"
        f"Text:\n{text}"
    )
    response = await llm_provider.complete(
        [{"role": "user", "content": prompt}], json_schema=CANDIDATE_SCHEMA
    )
    fields = (response.raw_json or {}).get("fields", [])
    return [
        CandidateField(
            label=field["label"],
            value=field["value"],
            unit=field.get("unit") or None,
            definition=field.get("definition") or None,
            document_id=document_id,
            page=page,
            snippet=text[:_SNIPPET_LENGTH],
        )
        for field in fields
    ]
