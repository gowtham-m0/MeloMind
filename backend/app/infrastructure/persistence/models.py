"""SQLAlchemy tables. The Alembic migrations in `backend/alembic/` create them."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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
    image_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProfileRow(Base):
    """A profile: the minimum personal data, and no health fields."""

    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("birth_year is null or birth_year >= 1900", name="profiles_birth_year"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    display_name: Mapped[str] = mapped_column(String(60))
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
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


class FeedRowRecord(Base):
    """A feed snapshot: the hero and rows as JSON. Deleted with its profile."""

    __tablename__ = "feeds"
    __table_args__ = (
        CheckConstraint("status in ('building', 'done', 'failed')", name="feeds_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    agent_run_id: Mapped[UUID] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(16))
    stale: Mapped[bool] = mapped_column(Boolean)
    hero: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    summary: Mapped[str] = mapped_column(Text)
    taste_tags: Mapped[list[str]] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CatalogItemRow(Base):
    """An item the app has shown, by ref: Qloo data kept on the server only, like the cache."""

    __tablename__ = "catalog_items"

    ref: Mapped[str] = mapped_column(String(120), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FeedbackRow(Base):
    """One signal: like, save, open, quiz pick, journal confirm, dislike or not interested."""

    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint(
            "kind in ('liked', 'unliked', 'saved', 'unsaved', 'opened', 'quiz_pick', "
            "'journal_confirmed', 'disliked', 'not_interested')",
            name="feedback_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    item_ref: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str | None] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(20))
    platform: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExclusionRow(Base):
    """An item marked "not interested". One per item per profile."""

    __tablename__ = "exclusions"
    __table_args__ = (UniqueConstraint("profile_id", "entity_ref", name="exclusions_profile_ref"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    entity_ref: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str | None] = mapped_column(String(16))
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


class JournalNodeRow(Base):
    """A journal node: an entry (with its text), a media item or a place. Private to its
    profile, and deleted with it."""

    __tablename__ = "journal_nodes"
    __table_args__ = (
        CheckConstraint(
            "kind in ('entry', 'artist', 'song', 'movie', 'tv_show', 'book', 'place')",
            name="journal_nodes_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    entry_date: Mapped[date | None] = mapped_column("date", Date)
    mood: Mapped[str | None] = mapped_column(String(30))
    year: Mapped[int | None] = mapped_column(SmallInteger)
    qloo_id: Mapped[str | None] = mapped_column(String(100))
    creator: Mapped[str | None] = mapped_column(String(200))
    image_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class JournalLinkRow(Base):
    """A link between two journal nodes. Deleted with either node."""

    __tablename__ = "journal_links"
    __table_args__ = (
        UniqueConstraint("from_id", "to_id", "kind", name="journal_links_from_to_kind"),
        CheckConstraint(
            "kind in ('mentions', 'because_of', 'liked', 'related')", name="journal_links_kind"
        ),
        CheckConstraint("source in ('user', 'agent', 'qloo', 'feed')", name="journal_links_source"),
        CheckConstraint(
            "status in ('suggested', 'confirmed', 'rejected')", name="journal_links_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    from_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("journal_nodes.id", ondelete="CASCADE"), index=True
    )
    to_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("journal_nodes.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
