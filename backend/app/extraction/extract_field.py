"""Structured extraction of one schema field's value for one document,
against a set of retrieved chunks (retrieval-augmented, JSON output)."""

from __future__ import annotations

from dataclasses import dataclass

from app.db.models import Chunk as ChunkRow
from app.llm.base import LLMProvider

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "raw_value": {"type": "string"},
        "raw_unit": {"type": "string"},
        "confidence": {"type": "number"},
        "source_snippet": {"type": "string"},
    },
    "required": ["found"],
}


@dataclass
class ExtractedValue:
    found: bool
    raw_value: str | None
    raw_unit: str | None
    confidence: float
    source_snippet: str | None
    source_chunk_id: str | None
    page: int | None


async def extract_field(
    llm_provider: LLMProvider,
    chunks: list[ChunkRow],
    field_name: str,
    field_definition: str,
) -> ExtractedValue:
    if not chunks:
        return ExtractedValue(
            found=False,
            raw_value=None,
            raw_unit=None,
            confidence=0.0,
            source_snippet=None,
            source_chunk_id=None,
            page=None,
        )

    context = "\n---\n".join(f"[p{c.page}] {c.text}" for c in chunks)
    prompt = (
        f'Field to extract: "{field_name}" -- {field_definition}\n\n'
        "Using ONLY the context below, extract this field's value for this "
        "document. If it is not present in the context, set found=false. "
        "Give raw_value and raw_unit exactly as written in the source text, "
        "a confidence between 0 and 1, and the exact source_snippet you "
        "read it from.\n\n"
        f"Context:\n{context}"
    )
    response = await llm_provider.complete(
        [{"role": "user", "content": prompt}], json_schema=EXTRACTION_SCHEMA
    )
    data = response.raw_json or {}

    if not data.get("found"):
        return ExtractedValue(
            found=False,
            raw_value=None,
            raw_unit=None,
            confidence=0.0,
            source_snippet=None,
            source_chunk_id=None,
            page=None,
        )

    snippet = data.get("source_snippet")
    matched = next((c for c in chunks if snippet and snippet in c.text), chunks[0])

    return ExtractedValue(
        found=True,
        raw_value=data.get("raw_value"),
        raw_unit=data.get("raw_unit") or None,
        confidence=float(data.get("confidence", 0.5)),
        source_snippet=snippet,
        source_chunk_id=matched.id,
        page=matched.page,
    )
