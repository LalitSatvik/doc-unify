"""Provider-agnostic interface for LLM and embedding calls.

Every other module (ingestion OCR cleanup, schema discovery, extraction,
the chat agent) talks to this interface only — never to a specific model
or SDK. `OllamaProvider` backs local/offline runs; `CloudProvider` backs
the hosted demo. Swapping providers is a config change, not a code change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolDefinition:
    """A function the LLM may call, described in JSON-schema-ish form."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    id: str


@dataclass
class LLMResponse:
    """Result of a chat/completion call.

    `text` holds a plain response; `tool_calls` is populated instead when
    the model chose to call one or more tools. `raw_json` is populated
    when the caller requested structured JSON output.
    """

    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_json: dict[str, Any] | None = None


class LLMProvider(ABC):
    """Chat/completion + embedding access, independent of backend."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Run one chat completion.

        - Pass `tools` to allow the model to call functions (chat agent).
        - Pass `json_schema` to force structured JSON output (extraction,
          candidate-field extraction, cluster review) — the response's
          `raw_json` will conform to the schema.
        - `tools` and `json_schema` are mutually exclusive per call.
        """
        raise NotImplementedError

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order."""
        raise NotImplementedError

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Dimensionality of vectors returned by `embed` (must match the
        pgvector column width configured for this deployment)."""
        raise NotImplementedError
