"""Allow any birth year from 1900; the service caps it at the current year.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("profiles_birth_year", "profiles", type_="check")
    op.create_check_constraint("profiles_birth_year", "profiles", "birth_year >= 1900")


def downgrade() -> None:
    op.drop_constraint("profiles_birth_year", "profiles", type_="check")
    op.create_check_constraint(
        "profiles_birth_year", "profiles", "birth_year between 1920 and 1990"
    )
