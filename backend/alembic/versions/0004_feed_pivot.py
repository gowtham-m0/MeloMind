"""The taste-dashboard pivot: feeds and the catalog in, sessions out, feedback as signals.

- New tables `feeds` and `catalog_items`, with RLS on and no policies, like the others.
- `sessions` and `session_items` are dropped.
- `feedback` becomes signals (liked, saved, opened…): the caregiver/person columns go. Old
  reactions mean nothing to the new product, so existing feedback and exclusions are deleted.
- `exclusions` lose their kind (every exclusion is "not interested") and gain the item's type.
- `favourites` gain an image URL; `profiles.birth_year` becomes optional.

There is no downgrade: the old session data can't be rebuilt.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SIGNALS = (
    "'liked', 'unliked', 'saved', 'unsaved', 'opened', 'quiz_pick', "
    "'journal_confirmed', 'disliked', 'not_interested'"
)


def upgrade() -> None:
    op.create_table(
        "feeds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.Uuid(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False),
        sa.Column("hero", postgresql.JSONB(), nullable=True),
        sa.Column("rows", postgresql.JSONB(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("taste_tags", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status in ('building', 'done', 'failed')", name="feeds_status"),
    )
    op.create_index("ix_feeds_profile_id", "feeds", ["profile_id"])
    op.create_table(
        "catalog_items",
        sa.Column("ref", sa.String(120), primary_key=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for table in ("feeds", "catalog_items"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute("DELETE FROM feedback")
    op.execute("DELETE FROM exclusions")
    op.drop_constraint("feedback_actor", "feedback", type_="check")
    op.drop_column("feedback", "session_id")
    op.drop_column("feedback", "actor")
    op.drop_column("feedback", "note")
    op.drop_column("feedback", "played_s")
    op.alter_column("feedback", "kind", type_=sa.String(20))
    op.add_column("feedback", sa.Column("platform", sa.String(32), nullable=True))
    op.create_check_constraint("feedback_kind", "feedback", f"kind in ({_SIGNALS})")

    op.drop_constraint("exclusions_kind", "exclusions", type_="check")
    op.drop_column("exclusions", "kind")
    op.drop_column("exclusions", "needs_review")
    op.add_column("exclusions", sa.Column("entity_type", sa.String(16), nullable=True))

    op.drop_table("session_items")
    op.drop_table("sessions")

    op.add_column("favourites", sa.Column("image_url", sa.String(500), nullable=True))
    op.drop_constraint("profiles_birth_year", "profiles", type_="check")
    op.alter_column("profiles", "birth_year", nullable=True)
    op.create_check_constraint(
        "profiles_birth_year", "profiles", "birth_year is null or birth_year >= 1900"
    )


def downgrade() -> None:
    raise NotImplementedError("The pivot can't be undone: session data was dropped.")
