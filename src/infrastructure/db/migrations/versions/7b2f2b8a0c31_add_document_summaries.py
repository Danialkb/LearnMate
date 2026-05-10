"""add document summaries"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7b2f2b8a0c31"
down_revision = "dbc5556a0f57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    document_summary_style = sa.Enum(
        "brief",
        "detailed",
        "bullets",
        name="document_summary_style",
    )
    document_summary_style.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "document_summaries",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("style", document_summary_style, nullable=False),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("source_document_version", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "style",
            "source_document_version",
            name="uq_document_summaries_document_style_version",
        ),
    )
    op.create_index(
        op.f("ix_document_summaries_document_id"),
        "document_summaries",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_document_summaries_document_id"),
        table_name="document_summaries",
    )
    op.drop_table("document_summaries")
    sa.Enum(name="document_summary_style").drop(op.get_bind(), checkfirst=True)
