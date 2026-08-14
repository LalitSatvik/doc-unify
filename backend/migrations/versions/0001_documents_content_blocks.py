"""documents + content_blocks

Revision ID: 0001
Revises:
Create Date: 2026-08-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector extension is created here (rather than deferred to the
    # embedding-phase migration) so every later migration can rely on it
    # already being present.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "ingested", "failed", name="document_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "content_blocks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(length=36),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column(
            "block_type",
            sa.Enum("text", "table", "image", name="block_type"),
            nullable=False,
        ),
        sa.Column("text", sa.String(), nullable=True),
        sa.Column("table", sa.JSON(), nullable=True),
        sa.Column("bbox", sa.JSON(), nullable=True),
    )
    op.create_index("ix_content_blocks_document_id", "content_blocks", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_content_blocks_document_id", table_name="content_blocks")
    op.drop_table("content_blocks")
    op.drop_table("documents")
    op.execute('DROP TYPE IF EXISTS "block_type"')
    op.execute('DROP TYPE IF EXISTS "document_status"')
    op.execute("DROP EXTENSION IF EXISTS vector")
