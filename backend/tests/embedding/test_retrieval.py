from sqlalchemy.dialects import postgresql

from app.embedding.retrieval import retrieve, similar_chunks_query
from tests.embedding.conftest import FakeLLMProvider


def test_similar_chunks_query_orders_by_cosine_distance() -> None:
    stmt = similar_chunks_query([0.1, 0.2], top_k=3)
    compiled = str(stmt.compile(dialect=postgresql.dialect()))

    assert "ORDER BY" in compiled
    assert "<=>" in compiled
    assert "chunks" in compiled


def test_similar_chunks_query_filters_by_document_ids_when_given() -> None:
    stmt = similar_chunks_query([0.1, 0.2], document_ids=["doc-1", "doc-2"])
    compiled = str(stmt.compile(dialect=postgresql.dialect()))

    assert "document_id" in compiled


async def test_retrieve_embeds_query_then_searches_by_vector(monkeypatch) -> None:
    captured = {}

    def fake_retrieve_by_vector(session, query_embedding, top_k=5, document_ids=None):
        captured["query_embedding"] = query_embedding
        captured["top_k"] = top_k
        return ["chunk-a", "chunk-b"]

    monkeypatch.setattr("app.embedding.retrieval.retrieve_by_vector", fake_retrieve_by_vector)

    fake_llm = FakeLLMProvider()
    result = await retrieve(session=None, llm_provider=fake_llm, query_text="Revenue", top_k=2)

    assert result == ["chunk-a", "chunk-b"]
    assert captured["query_embedding"] == [float(len("Revenue") % 7), float(hash("Revenue") % 7)]
    assert captured["top_k"] == 2
    assert fake_llm.embed_calls == [["Revenue"]]
