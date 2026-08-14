"""A fully scripted `LLMProvider` for tests that need multiple, distinct
`complete()`/`embed()` calls in sequence (schema discovery, extraction,
the chat agent) -- no live model, fully deterministic."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.llm.base import LLMProvider, LLMResponse, ToolDefinition


class ScriptedLLMProvider(LLMProvider):
    def __init__(
        self,
        complete_responses: list[LLMResponse] | None = None,
        embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
    ) -> None:
        self._complete_responses = list(complete_responses or [])
        self._embed_fn = embed_fn or (lambda texts: [[float(len(t))] for t in texts])
        self.complete_calls: list[list[dict[str, str]]] = []
        self.embed_calls: list[list[str]] = []

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        self.complete_calls.append(messages)
        if not self._complete_responses:
            raise AssertionError("ScriptedLLMProvider.complete called more times than scripted")
        return self._complete_responses.pop(0)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(texts)
        return self._embed_fn(texts)

    @property
    def embedding_dim(self) -> int:
        return 2
