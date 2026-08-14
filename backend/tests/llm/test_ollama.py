import json

import httpx
import pytest

from app.llm.base import ToolDefinition
from app.llm.ollama import OllamaProvider


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama.test")


@pytest.mark.asyncio
async def test_complete_returns_plain_text() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "The revenue was $12,345."}},
        )

    provider = OllamaProvider(chat_model="qwen2.5:7b", embed_model="nomic-embed-text")
    provider._client = _client(handler)

    response = await provider.complete([{"role": "user", "content": "What was revenue?"}])

    assert response.text == "The revenue was $12,345."
    assert response.tool_calls == []
    assert captured["url"].endswith("/api/chat")
    assert captured["body"]["model"] == "qwen2.5:7b"
    assert captured["body"]["stream"] is False
    assert captured["body"]["messages"] == [{"role": "user", "content": "What was revenue?"}]


@pytest.mark.asyncio
async def test_complete_with_tools_sends_tool_schema_and_parses_tool_calls() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "get_revenue", "arguments": {"doc_id": "d1"}}}
                    ],
                }
            },
        )

    provider = OllamaProvider(chat_model="qwen2.5:7b", embed_model="nomic-embed-text")
    provider._client = _client(handler)

    tools = [
        ToolDefinition(
            name="get_revenue",
            description="Look up revenue for a document",
            parameters={"type": "object", "properties": {"doc_id": {"type": "string"}}},
        )
    ]

    response = await provider.complete(
        [{"role": "user", "content": "revenue?"}], tools=tools
    )

    assert captured["body"]["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "get_revenue",
                "description": "Look up revenue for a document",
                "parameters": {"type": "object", "properties": {"doc_id": {"type": "string"}}},
            },
        }
    ]
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "get_revenue"
    assert response.tool_calls[0].arguments == {"doc_id": "d1"}
    assert response.tool_calls[0].id


@pytest.mark.asyncio
async def test_complete_with_json_schema_parses_raw_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"label": "Revenue", "value": 12345}),
                }
            },
        )

    provider = OllamaProvider(chat_model="qwen2.5:7b", embed_model="nomic-embed-text")
    provider._client = _client(handler)

    schema = {"type": "object", "properties": {"label": {"type": "string"}}}
    response = await provider.complete(
        [{"role": "user", "content": "extract"}], json_schema=schema
    )

    assert response.raw_json == {"label": "Revenue", "value": 12345}


@pytest.mark.asyncio
async def test_embed_returns_one_vector_per_input() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["input"] == ["Revenue", "Net Sales"]
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    provider = OllamaProvider(chat_model="qwen2.5:7b", embed_model="nomic-embed-text")
    provider._client = _client(handler)

    vectors = await provider.embed(["Revenue", "Net Sales"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_embedding_dim_defaults_for_known_model() -> None:
    provider = OllamaProvider(chat_model="qwen2.5:7b", embed_model="nomic-embed-text")
    assert provider.embedding_dim == 768
