from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk as ChunkRow
from app.db.repository import create_document, save_content_blocks
from app.embedding.pipeline import embed_and_store
from app.ingestion.base import BlockType, ContentBlock
from tests.embedding.conftest import FakeLLMProvider


async def test_embed_and_store_persists_one_chunk_per_row(
    session: Session, fake_llm: FakeLLMProvider
) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")
    blocks = save_content_blocks(
        session,
        document.id,
        [
            ContentBlock(document_id=document.id, page=1, block_type=BlockType.TEXT, text="Revenue"),
            ContentBlock(document_id=document.id, page=2, block_type=BlockType.TEXT, text="Net Sales"),
        ],
    )

    rows = await embed_and_store(session, fake_llm, document.id, blocks)

    assert len(rows) == 2
    assert {r.text for r in rows} == {"Revenue", "Net Sales"}
    assert all(r.document_id == document.id for r in rows)
    assert {r.content_block_id for r in rows} == {b.id for b in blocks}
    assert all(len(r.embedding) == 2 for r in rows)

    persisted = session.scalars(select(ChunkRow)).all()
    assert len(persisted) == 2


async def test_embed_and_store_returns_empty_for_no_blocks(
    session: Session, fake_llm: FakeLLMProvider
) -> None:
    document = create_document(session, filename="report.pdf", content_type="application/pdf")

    rows = await embed_and_store(session, fake_llm, document.id, [])

    assert rows == []
    assert fake_llm.embed_calls == []
