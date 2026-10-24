"""Schemas for the feed, item details, feedback, the library and the taste quiz."""

from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.application.ports import PlayableMedia
from app.application.services.feedback import FeedbackEffect
from app.application.services.items import ItemDetail
from app.application.services.library import Library
from app.application.services.quiz import QuizStep
from app.domain.feed import (
    Feed,
    FeedItem,
    FeedRow,
    FeedStatus,
    ImageAspect,
    ItemSource,
    LinkKind,
    PlatformLink,
    RowPlacement,
)
from app.domain.feedback import Signal
from app.domain.models import EntityType

States = Mapping[str, frozenset[Signal]]
Ref = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]

# Signals the client may send. The quiz and journal signals are recorded by the app itself.
ClientSignal = Literal[
    "liked", "unliked", "saved", "unsaved", "opened", "disliked", "not_interested"
]


class PlatformLinkOut(BaseModel):
    """Where to find an item. `search` links are labelled "Search on …"."""

    platform: str
    label: str
    url: str
    kind: LinkKind

    @classmethod
    def from_domain(cls, link: PlatformLink) -> Self:
        """Build from the domain value."""
        return cls(platform=link.platform, label=link.label, url=link.url, kind=link.kind)


class BecauseOfOut(BaseModel):
    """The item behind a pick."""

    ref: str
    title: str


class FeedItemOut(BaseModel):
    """One card. `liked` and `saved` show the user's current state for the heart and bookmark.

    Songs add `creator` (the credited artists) and `preview_url`: Apple's 30-second preview, to
    stream only on tap, next to the Apple Music link, credited "courtesy of iTunes".
    """

    ref: str
    title: str
    entity_type: EntityType
    year: int | None
    image_url: str | None
    image_aspect: ImageAspect
    reason: str
    because_of: BecauseOfOut | None
    affinity: float | None
    popularity: float | None
    tags: list[str]
    description: str | None
    source: ItemSource
    links: list[PlatformLinkOut]
    liked: bool
    saved: bool
    creator: str | None = None
    preview_url: str | None = None

    @classmethod
    def from_domain(cls, item: FeedItem, states: States) -> Self:
        """Build from the domain value and the user's liked and saved items."""
        state = states.get(item.ref, frozenset())
        because = (
            BecauseOfOut(ref=item.because_of_ref, title=item.because_of_title)
            if item.because_of_ref and item.because_of_title
            else None
        )
        return cls(
            ref=item.ref,
            title=item.title,
            entity_type=item.entity_type,
            year=item.year,
            image_url=item.image_url,
            image_aspect=item.image_aspect,
            reason=item.reason,
            because_of=because,
            affinity=round(item.affinity, 3) if item.affinity is not None else None,
            popularity=round(item.popularity, 3) if item.popularity is not None else None,
            tags=list(item.tags),
            description=item.description,
            source=item.source,
            links=[PlatformLinkOut.from_domain(link) for link in item.links],
            liked=Signal.LIKED in state,
            saved=Signal.SAVED in state,
            creator=item.creator,
            preview_url=item.preview_url,
        )


class FeedRowOut(BaseModel):
    """A titled row. `rail` rows go in the right rail."""

    key: str
    title: str
    subtitle: str
    placement: RowPlacement
    items: list[FeedItemOut]

    @classmethod
    def from_domain(cls, row: FeedRow, states: States) -> Self:
        """Build from the domain value."""
        return cls(
            key=row.key,
            title=row.title,
            subtitle=row.subtitle,
            placement=row.placement,
            items=[FeedItemOut.from_domain(item, states) for item in row.items],
        )


class FeedOut(BaseModel):
    """A feed snapshot. `stale` is true after feedback since it was built."""

    id: UUID
    profile_id: UUID
    status: FeedStatus
    stale: bool
    agent_run_id: UUID
    summary: str
    taste_tags: list[str]
    hero: FeedItemOut | None
    rows: list[FeedRowOut]
    created_at: datetime

    @classmethod
    def from_domain(cls, feed: Feed, states: States) -> Self:
        """Build from the domain entity."""
        return cls(
            id=feed.id,
            profile_id=feed.profile_id,
            status=feed.status,
            stale=feed.stale,
            agent_run_id=feed.agent_run_id,
            summary=feed.summary,
            taste_tags=list(feed.taste_tags),
            hero=FeedItemOut.from_domain(feed.hero, states) if feed.hero else None,
            rows=[FeedRowOut.from_domain(row, states) for row in feed.rows],
            created_at=feed.created_at,
        )


class ItemDetailOut(FeedItemOut):
    """A card plus more like it ("After this song" for a song), an artist's top songs, and
    whether a YouTube preview can be looked up."""

    more_like_this: list[FeedItemOut]
    preview_available: bool
    songs: list[FeedItemOut]

    @classmethod
    def from_detail(cls, detail: ItemDetail, states: States) -> Self:
        """Build from the service result."""
        card = FeedItemOut.from_domain(detail.item, states)
        return cls(
            **card.model_dump(),
            more_like_this=[
                FeedItemOut.from_domain(item, states) for item in detail.more_like_this
            ],
            preview_available=detail.preview_available,
            songs=[FeedItemOut.from_domain(item, states) for item in detail.songs],
        )


class PreviewOut(BaseModel):
    """A video to embed for the optional preview."""

    provider: Literal["youtube", "demo"]
    video_id: str
    title: str
    duration_s: int

    @classmethod
    def from_media(cls, media: PlayableMedia) -> Self:
        """Build from the media port's value."""
        return cls(
            provider=media.provider,
            video_id=media.video_id,
            title=media.title,
            duration_s=media.duration_s,
        )


class FeedbackIn(BaseModel):
    """One signal for an item. `platform` is the link used, for `opened`."""

    ref: Ref
    title: Title
    entity_type: EntityType | None = None
    signal: ClientSignal
    platform: Annotated[str, StringConstraints(max_length=32)] | None = None


class FeedbackOut(BaseModel):
    """What the signal did."""

    ok: bool = True
    counted: bool
    effect: str
    stale: bool

    @classmethod
    def from_effect(cls, effect: FeedbackEffect) -> Self:
        """Build from the service result."""
        return cls(counted=effect.counted, effect=effect.effect, stale=effect.stale)


class LibraryOut(BaseModel):
    """Liked and saved items, newest first."""

    liked: list[FeedItemOut]
    saved: list[FeedItemOut]

    @classmethod
    def from_library(cls, library: Library, states: States) -> Self:
        """Build from the service result."""
        return cls(
            liked=[FeedItemOut.from_domain(item, states) for item in library.liked],
            saved=[FeedItemOut.from_domain(item, states) for item in library.saved],
        )


class QuizIn(BaseModel):
    """Every ref shown so far, and the one just picked (none for the first pair)."""

    picked_ref: Ref | None = None
    shown_refs: list[Ref] = Field(default_factory=list, max_length=40)


class QuizStepOut(BaseModel):
    """The next pair, or `done`."""

    pair: list[FeedItemOut] | None
    round: int
    rounds: int
    done: bool

    @classmethod
    def from_step(cls, step: QuizStep) -> Self:
        """Build from the service result."""
        return cls(
            pair=[FeedItemOut.from_domain(item, {}) for item in step.pair] if step.pair else None,
            round=step.round,
            rounds=step.rounds,
            done=step.done,
        )
