from app.db.models import Chunk as ChunkRow
from app.extraction.extract_field import extract_field
from app.llm.base import LLMResponse
from tests.support.scripted_llm import ScriptedLLMProvider


def _chunk(id_: str, page: int, text: str) -> ChunkRow:
    return ChunkRow(id=id_, document_id="doc-1", content_block_id="cb-1", page=page, text=text, embedding=[0.0])


async def test_extract_field_matches_snippet_back_to_its_chunk() -> None:
    chunks = [
        _chunk("c1", 1, "Headcount: 500 employees"),
        _chunk("c2", 3, "Total Revenue was $12,345K in the quarter."),
    ]
    provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(
                raw_json={
                    "found": True,
                    "raw_value": "12,345",
                    "raw_unit": "$K",
                    "confidence": 0.9,
                    "source_snippet": "Total Revenue was $12,345K in the quarter.",
                }
            )
        ]
    )

    result = await extract_field(provider, chunks, field_name="Total Revenue", field_definition="Revenue")

    assert result.found is True
    assert result.raw_value == "12,345"
    assert result.raw_unit == "$K"
    assert result.confidence == 0.9
    assert result.source_chunk_id == "c2"
    assert result.page == 3


async def test_extract_field_not_found_returns_found_false() -> None:
    chunks = [_chunk("c1", 1, "Headcount: 500 employees")]
    provider = ScriptedLLMProvider(complete_responses=[LLMResponse(raw_json={"found": False})])

    result = await extract_field(provider, chunks, field_name="Total Revenue", field_definition="Revenue")

    assert result.found is False
    assert result.raw_value is None
    assert result.source_chunk_id is None
