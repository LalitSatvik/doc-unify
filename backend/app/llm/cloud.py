"""`LLMProvider` backed by an OpenAI-compatible hosted API (used by the
free-tier hosted demo — e.g. Groq). Same interface as `OllamaProvider`;
callers never know which one they're talking to.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.llm.base import LLMProvider, LLMResponse, ToolCall, ToolDefinition


class CloudProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        chat_model: str,
        embed_model: str = "",
        embedding_dim: int = 768,
        timeout: float = 120.0,
    ) -> None:
        self._chat_model = chat_model
        self._embed_model = embed_model
        self._embedding_dim = embedding_dim
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        if tools and json_schema:
            raise ValueError("tools and json_schema are mutually exclusive per call")

        payload: dict[str, Any] = {
            "model": self._chat_model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = [_tool_definition_to_openai(tool) for tool in tools]
        if json_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": json_schema},
            }

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]

        tool_calls = [
            ToolCall(
                name=call["function"]["name"],
                arguments=json.loads(call["function"]["arguments"]),
                id=call["id"],
            )
            for call in message.get("tool_calls") or []
        ]

        raw_json = None
        if json_schema and message.get("content"):
            raw_json = json.loads(message["content"])

        return LLMResponse(
            text=message.get("content") if not tool_calls and not json_schema else None,
            tool_calls=tool_calls,
            raw_json=raw_json,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.post(
            "/embeddings", json={"model": self._embed_model, "input": texts}
        )
        response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in data]

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim


def _tool_definition_to_openai(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }
