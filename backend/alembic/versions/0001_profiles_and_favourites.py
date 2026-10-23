"""Profiles and favourites, with row-level security on and no policies.

RLS with no policies blocks Supabase's public API (anon and authenticated roles) from these
tables, and from Alembic's own version table. The backend connects as the database owner,
which RLS doesn't restrict.

Revision ID: 0001
Revises:
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(60), nullable=False),
        sa.Column("birth_year", sa.SmallInteger(), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("places_lived", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("languages", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("birth_year between 1920 and 1990", name="profiles_birth_year"),
    )
    op.create_index("ix_profiles_owner_id", "profiles", ["owner_id"])

    op.create_table(
        "favourites",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.Uuid(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("qloo_id", sa.String(100), nullable=True),
        sa.Column("song_title", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind in ('artist', 'song', 'movie', 'tv_show', 'book')", name="favourites_kind"
        ),
    )
    op.create_index("ix_favourites_profile_id", "favourites", ["profile_id"])

    op.execute("ALTER TABLE profiles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE favourites ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("favourites")
    op.drop_table("profiles")
