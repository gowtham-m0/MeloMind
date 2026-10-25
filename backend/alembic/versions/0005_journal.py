"""The journal: `journal_nodes` (entries, media items, places) and `journal_links`.

Both have RLS on and no policies, like the other tables: only the backend reads them. A link is
unique per `(from_id, to_id, kind)`, so a rejected suggestion stays rejected.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "journal_nodes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.Uuid(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("mood", sa.String(30), nullable=True),
        sa.Column("year", sa.SmallInteger(), nullable=True),
        sa.Column("qloo_id", sa.String(100), nullable=True),
        sa.Column("creator", sa.String(200), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind in ('entry', 'artist', 'song', 'movie', 'tv_show', 'book', 'place')",
            name="journal_nodes_kind",
        ),
    )
    op.create_index("ix_journal_nodes_profile_id", "journal_nodes", ["profile_id"])
    op.create_table(
        "journal_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.Uuid(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "from_id",
            sa.Uuid(),
            sa.ForeignKey("journal_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_id",
            sa.Uuid(),
            sa.ForeignKey("journal_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("from_id", "to_id", "kind", name="journal_links_from_to_kind"),
        sa.CheckConstraint(
            "kind in ('mentions', 'because_of', 'liked', 'related')", name="journal_links_kind"
        ),
        sa.CheckConstraint(
            "source in ('user', 'agent', 'qloo', 'feed')", name="journal_links_source"
        ),
        sa.CheckConstraint(
            "status in ('suggested', 'confirmed', 'rejected')", name="journal_links_status"
        ),
    )
    op.create_index("ix_journal_links_profile_id", "journal_links", ["profile_id"])
    op.create_index("ix_journal_links_from_id", "journal_links", ["from_id"])
    op.create_index("ix_journal_links_to_id", "journal_links", ["to_id"])
    for table in ("journal_nodes", "journal_links"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("journal_links")
    op.drop_table("journal_nodes")
