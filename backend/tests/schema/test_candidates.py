from app.llm.base import LLMResponse
from app.schema.candidates import extract_candidates
from tests.support.scripted_llm import ScriptedLLMProvider


async def test_extract_candidates_parses_fields_from_json_response() -> None:
    provider = ScriptedLLMProvider(
        complete_responses=[
            LLMResponse(
                raw_json={
                    "fields": [
                        {
                            "label": "Total Revenue",
                            "value": "12,345",
                            "unit": "$K",
                            "definition": "Total revenue for the quarter",
                        }
                    ]
                }
            )
        ]
    )

    candidates = await extract_candidates(
        provider, document_id="doc-1", page=3, text="Total Revenue: $12,345K"
    )

    assert len(candidates) == 1
    c = candidates[0]
    assert c.label == "Total Revenue"
    assert c.value == "12,345"
    assert c.unit == "$K"
    assert c.definition == "Total revenue for the quarter"
    assert c.document_id == "doc-1"
    assert c.page == 3
    assert "Total Revenue" in c.snippet


async def test_extract_candidates_returns_empty_list_when_no_fields_found() -> None:
    provider = ScriptedLLMProvider(complete_responses=[LLMResponse(raw_json={"fields": []})])

    candidates = await extract_candidates(
        provider, document_id="doc-1", page=1, text="Just narrative text, no figures."
    )

    assert candidates == []
