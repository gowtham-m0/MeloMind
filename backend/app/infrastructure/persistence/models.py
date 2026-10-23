"""SQLAlchemy tables. The Alembic migrations in `backend/alembic/` create them."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for every table."""


class FavouriteRow(Base):
    """A favourite. Deleted by the database when its profile is deleted."""

    __tablename__ = "favourites"
    __table_args__ = (
        CheckConstraint(
            "kind in ('artist', 'song', 'movie', 'tv_show', 'book')", name="favourites_kind"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16))
    qloo_id: Mapped[str | None] = mapped_column(String(100))
    song_title: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProfileRow(Base):
    """A profile: the minimum personal data, and no health fields."""

    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("birth_year between 1920 and 1990", name="profiles_birth_year"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    display_name: Mapped[str] = mapped_column(String(60))
    birth_year: Mapped[int] = mapped_column(SmallInteger)
    country_code: Mapped[str | None] = mapped_column(String(2))
    places_lived: Mapped[list[str]] = mapped_column(ARRAY(Text))
    languages: Mapped[list[str]] = mapped_column(ARRAY(Text))
    is_demo: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    favourites: Mapped[list[FavouriteRow]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by=FavouriteRow.created_at,
    )
