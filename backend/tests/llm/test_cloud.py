import json

import httpx
import pytest

from app.llm.base import ToolDefinition
from app.llm.cloud import CloudProvider


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://cloud.test",
        headers={"Authorization": "Bearer secret"},
    )


@pytest.mark.asyncio
async def test_complete_returns_plain_text() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "It was $12,345."}}]},
        )

    provider = CloudProvider(api_key="secret", base_url="http://cloud.test", chat_model="llama-3.1-70b")
    provider._client = _client(handler)

    response = await provider.complete([{"role": "user", "content": "revenue?"}])

    assert response.text == "It was $12,345."
    assert captured["url"].endswith("/chat/completions")
    assert captured["body"]["model"] == "llama-3.1-70b"
    assert captured["auth"] == "Bearer secret"


@pytest.mark.asyncio
async def test_complete_with_tools_parses_tool_calls() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "get_revenue",
                                        "arguments": json.dumps({"doc_id": "d1"}),
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    provider = CloudProvider(api_key="secret", base_url="http://cloud.test", chat_model="m")
    provider._client = _client(handler)

    tools = [ToolDefinition(name="get_revenue", description="x", parameters={"type": "object"})]
    response = await provider.complete([{"role": "user", "content": "revenue?"}], tools=tools)

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "get_revenue"
    assert response.tool_calls[0].arguments == {"doc_id": "d1"}
    assert response.tool_calls[0].id == "call_1"


@pytest.mark.asyncio
async def test_complete_with_json_schema_requests_json_object_and_parses() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": json.dumps({"label": "Revenue"})}}
                ]
            },
        )

    provider = CloudProvider(api_key="secret", base_url="http://cloud.test", chat_model="m")
    provider._client = _client(handler)

    schema = {"type": "object", "properties": {"label": {"type": "string"}}}
    response = await provider.complete([{"role": "user", "content": "extract"}], json_schema=schema)

    assert response.raw_json == {"label": "Revenue"}
    assert captured["body"]["response_format"]["type"] == "json_schema"


@pytest.mark.asyncio
async def test_embed_returns_vectors_in_index_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.3, 0.4]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            },
        )

    provider = CloudProvider(
        api_key="secret", base_url="http://cloud.test", chat_model="m", embed_model="e"
    )
    provider._client = _client(handler)

    vectors = await provider.embed(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
