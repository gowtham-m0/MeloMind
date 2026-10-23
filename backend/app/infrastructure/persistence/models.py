"""SQLAlchemy tables. The Alembic migrations in `backend/alembic/` create them."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
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


class SessionItemRow(Base):
    """One item of a session, in order. Deleted with its session."""

    __tablename__ = "session_items"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger)
    ref: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(Text)
    signal: Mapped[str] = mapped_column(String(200))
    release_year: Mapped[int | None] = mapped_column(SmallInteger)
    age_at_release: Mapped[int | None] = mapped_column(SmallInteger)
    prompt: Mapped[str | None] = mapped_column(Text)
    media_provider: Mapped[str | None] = mapped_column(String(16))
    media_ref: Mapped[str | None] = mapped_column(String(64))
    media_title: Mapped[str | None] = mapped_column(String(200))
    media_duration_s: Mapped[int | None] = mapped_column(Integer)
    duration_s: Mapped[int] = mapped_column(Integer)


class SessionRow(Base):
    """A planned session or warm-up set. Deleted by the database with its profile."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "status in ('planning', 'draft', 'approved', 'in_progress', 'completed', 'failed')",
            name="sessions_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[str] = mapped_column(String(32))
    target_minutes: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(16))
    agent_run_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    items: Mapped[list[SessionItemRow]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by=SessionItemRow.position,
    )


class FeedbackRow(Base):
    """A caregiver reaction or a person signal, with who gave it."""

    __tablename__ = "feedback"
    __table_args__ = (CheckConstraint("actor in ('caregiver', 'person')", name="feedback_actor"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="SET NULL")
    )
    item_ref: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str | None] = mapped_column(String(16))
    actor: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(Text)
    played_s: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExclusionRow(Base):
    """An item the caregiver rejected or hid. One per item per profile."""

    __tablename__ = "exclusions"
    __table_args__ = (
        UniqueConstraint("profile_id", "entity_ref", name="exclusions_profile_ref"),
        CheckConstraint("kind in ('rejected', 'hidden')", name="exclusions_kind"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    entity_ref: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(16))
    needs_review: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentRunRow(Base):
    """One workflow run and its plain-English log."""

    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MediaCacheRow(Base):
    """A cached media lookup. `video_id` is null when nothing playable was found."""

    __tablename__ = "media_cache"

    query_key: Mapped[str] = mapped_column(String(300), primary_key=True)
    provider: Mapped[str | None] = mapped_column(String(16))
    video_id: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(300))
    duration_s: Mapped[int | None] = mapped_column(Integer)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class QlooCacheRow(Base):
    """Parsed Qloo results for one request, kept on the server only."""

    __tablename__ = "qloo_cache"

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
