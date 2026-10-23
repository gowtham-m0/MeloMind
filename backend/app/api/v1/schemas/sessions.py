"""Request and response schemas for sessions, their items and caregiver reactions."""

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.application.services.feedback import FeedbackEffect
from app.domain.feedback import Reaction
from app.domain.models import EntityType
from app.domain.sessions import ItemSource, MediaRef, Session, SessionItem, SessionStatus

PromptText = Annotated[str, StringConstraints(max_length=300)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
ITEMS_MAX = 50


class MediaOut(BaseModel):
    """A playable video. `provider` is `youtube`, or `demo` for stand-in media in demo mode."""

    provider: str
    ref: str
    duration_s: int
    title: str

    @classmethod
    def from_domain(cls, media: MediaRef) -> Self:
        """Build from the domain value."""
        return cls(
            provider=media.provider, ref=media.ref, duration_s=media.duration_s, title=media.title
        )


class SessionItemOut(BaseModel):
    """One item. A book has no media: it's a short conversation slot."""

    id: UUID
    position: int
    ref: str
    title: str
    entity_type: EntityType
    release_year: int | None
    age_at_release: int | None
    reason: str
    prompt: str | None
    source: ItemSource
    media: MediaOut | None
    duration_s: int

    @classmethod
    def from_domain(cls, item: SessionItem) -> Self:
        """Build from the domain entity."""
        return cls(
            id=item.id,
            position=item.position,
            ref=item.ref,
            title=item.title,
            entity_type=item.entity_type,
            release_year=item.release_year,
            age_at_release=item.age_at_release,
            reason=item.reason,
            prompt=item.prompt,
            source=item.source,
            media=MediaOut.from_domain(item.media) if item.media else None,
            duration_s=item.duration_s,
        )


class SessionDraftOut(BaseModel):
    """A session or warm-up set, with its items in order."""

    id: UUID
    profile_id: UUID
    status: SessionStatus
    mode: str
    target_minutes: int
    total_duration_s: int
    agent_run_id: UUID | None
    items: list[SessionItemOut]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, session: Session) -> Self:
        """Build from the domain entity."""
        return cls(
            id=session.id,
            profile_id=session.profile_id,
            status=session.status,
            mode=session.mode,
            target_minutes=session.target_minutes,
            total_duration_s=session.total_duration_s,
            agent_run_id=session.agent_run_id,
            items=[SessionItemOut.from_domain(item) for item in session.items],
            created_at=session.created_at,
            updated_at=session.updated_at,
        )


class SessionSummaryOut(BaseModel):
    """A session in the history list."""

    id: UUID
    mode: str
    status: SessionStatus
    item_count: int
    total_duration_s: int
    created_at: datetime

    @classmethod
    def from_domain(cls, session: Session) -> Self:
        """Build from the domain entity."""
        return cls(
            id=session.id,
            mode=session.mode,
            status=session.status,
            item_count=len(session.items),
            total_duration_s=session.total_duration_s,
            created_at=session.created_at,
        )


class PlanRequestIn(BaseModel):
    """Plan a session. `mode` is `standard` or `warmup`. `instructions` is accepted now and
    used from Phase 4."""

    mode: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] = (
        "standard"
    )
    target_minutes: Literal[10, 20, 30] = 20
    instructions: Annotated[str, StringConstraints(max_length=500)] | None = None


class ItemsPatch(BaseModel):
    """Changes to a draft: items to remove, the new order, and edited prompts by item ID."""

    order: list[UUID] | None = Field(default=None, max_length=ITEMS_MAX)
    removed: list[UUID] | None = Field(default=None, max_length=ITEMS_MAX)
    prompts: dict[UUID, PromptText] | None = None


class ReactionIn(BaseModel):
    """The caregiver's reaction to an item."""

    reaction: Reaction
    note: Note | None = None


class FeedbackOut(BaseModel):
    """`counted` is false when a signal was ignored (a late skip, or a repeat the same day)."""

    ok: bool = True
    counted: bool
    effect: str

    @classmethod
    def from_effect(cls, effect: FeedbackEffect) -> Self:
        """Build from the service's answer."""
        return cls(counted=effect.counted, effect=effect.effect)
