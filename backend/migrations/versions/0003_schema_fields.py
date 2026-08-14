"""schema_fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schema_fields",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("definition", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("proposed", "approved", "rejected", name="schema_field_status"),
            nullable=False,
        ),
        sa.Column("has_conflict", sa.Boolean(), nullable=False),
        sa.Column("conflict_reason", sa.String(), nullable=True),
        sa.Column("member_labels", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("schema_fields")
    op.execute('DROP TYPE IF EXISTS "schema_field_status"')
