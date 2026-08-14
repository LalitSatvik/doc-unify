"""`LLMProvider` backed by a local Ollama server. This is the default,
fully-offline path — every model call this app makes goes through
`app.llm.base.LLMProvider`, and this is one implementation of it.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from app.llm.base import LLMProvider, LLMResponse, ToolCall, ToolDefinition

# Dimensionality of common local embedding models, for convenience; pass
# `embedding_dim` explicitly to `OllamaProvider` to override.
_KNOWN_EMBEDDING_DIMS = {
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "all-minilm": 384,
}


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        chat_model: str,
        embed_model: str,
        base_url: str = "http://localhost:11434",
        embedding_dim: int | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._chat_model = chat_model
        self._embed_model = embed_model
        self._embedding_dim = embedding_dim or _KNOWN_EMBEDDING_DIMS.get(embed_model, 768)
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

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
            "stream": False,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = [_tool_definition_to_ollama(tool) for tool in tools]
        if json_schema:
            payload["format"] = json_schema

        response = await self._client.post("/api/chat", json=payload)
        response.raise_for_status()
        message = response.json()["message"]

        tool_calls = [
            ToolCall(
                name=call["function"]["name"],
                arguments=call["function"]["arguments"],
                id=str(uuid.uuid4()),
            )
            for call in message.get("tool_calls", [])
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
            "/api/embed", json={"model": self._embed_model, "input": texts}
        )
        response.raise_for_status()
        return response.json()["embeddings"]

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim


def _tool_definition_to_ollama(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }
