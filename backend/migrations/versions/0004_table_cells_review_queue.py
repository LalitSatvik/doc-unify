"""table_cells + review_queue

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "table_cells",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "document_id", sa.String(length=36), sa.ForeignKey("documents.id"), nullable=False
        ),
        sa.Column(
            "schema_field_id",
            sa.String(length=36),
            sa.ForeignKey("schema_fields.id"),
            nullable=False,
        ),
        sa.Column("raw_value", sa.String(), nullable=True),
        sa.Column("raw_unit", sa.String(), nullable=True),
        sa.Column("normalized_value", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "source_chunk_id", sa.String(length=36), sa.ForeignKey("chunks.id"), nullable=True
        ),
        sa.Column("source_snippet", sa.String(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_table_cells_document_id", "table_cells", ["document_id"])
    op.create_index("ix_table_cells_schema_field_id", "table_cells", ["schema_field_id"])

    op.create_table(
        "review_queue",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "table_cell_id",
            sa.String(length=36),
            sa.ForeignKey("table_cells.id"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("review_queue")
    op.drop_index("ix_table_cells_schema_field_id", table_name="table_cells")
    op.drop_index("ix_table_cells_document_id", table_name="table_cells")
    op.drop_table("table_cells")
