from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.llm.base import LLMProvider, LLMResponse, ToolDefinition


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


class FakeLLMProvider(LLMProvider):
    """Deterministic embedding: vector = [len(text) % 7, hash(text) % 7]."""

    def __init__(self) -> None:
        self.embed_calls: list[list[str]] = []

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        raise NotImplementedError

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(texts)
        return [[float(len(t) % 7), float(hash(t) % 7)] for t in texts]

    @property
    def embedding_dim(self) -> int:
        return 2


@pytest.fixture()
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider()
