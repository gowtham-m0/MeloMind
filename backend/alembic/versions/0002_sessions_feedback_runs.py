"""Sessions, feedback, exclusions, agent runs and the server-side caches, with RLS on.

Like 0001, row-level security is on with no policies, so Supabase's public API can't reach these
tables; the backend connects as the database owner.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "sessions",
    "session_items",
    "feedback",
    "exclusions",
    "agent_runs",
    "media_cache",
    "qloo_cache",
)


def _profile_fk() -> sa.Column:
    return sa.Column(
        "profile_id", sa.Uuid(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _profile_fk(),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("target_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('planning', 'draft', 'approved', 'in_progress', 'completed', 'failed')",
            name="sessions_status",
        ),
    )
    op.create_index("ix_sessions_profile_id", "sessions", ["profile_id"])

    op.create_table(
        "session_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("ref", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("entity_type", sa.String(16), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("signal", sa.String(200), nullable=False),
        sa.Column("release_year", sa.SmallInteger(), nullable=True),
        sa.Column("age_at_release", sa.SmallInteger(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("media_provider", sa.String(16), nullable=True),
        sa.Column("media_ref", sa.String(64), nullable=True),
        sa.Column("media_title", sa.String(200), nullable=True),
        sa.Column("media_duration_s", sa.Integer(), nullable=True),
        sa.Column("duration_s", sa.Integer(), nullable=False),
    )
    op.create_index("ix_session_items_session_id", "session_items", ["session_id"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _profile_fk(),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("item_ref", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("entity_type", sa.String(16), nullable=True),
        sa.Column("actor", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("played_s", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("actor in ('caregiver', 'person')", name="feedback_actor"),
    )
    op.create_index("ix_feedback_profile_id", "feedback", ["profile_id"])

    op.create_table(
        "exclusions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _profile_fk(),
        sa.Column("entity_ref", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("profile_id", "entity_ref", name="exclusions_profile_ref"),
        sa.CheckConstraint("kind in ('rejected', 'hidden')", name="exclusions_kind"),
    )
    op.create_index("ix_exclusions_profile_id", "exclusions", ["profile_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _profile_fk(),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_profile_id", "agent_runs", ["profile_id"])

    op.create_table(
        "media_cache",
        sa.Column("query_key", sa.String(300), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=True),
        sa.Column("video_id", sa.String(64), nullable=True),
        sa.Column("title", sa.String(300), nullable=True),
        sa.Column("duration_s", sa.Integer(), nullable=True),
        sa.Column("cached_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "qloo_cache",
        sa.Column("cache_key", sa.String(64), primary_key=True),
        sa.Column("rows", postgresql.JSONB(), nullable=False),
        sa.Column("cached_at", sa.DateTime(timezone=True), nullable=False),
    )

    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_table(table)
