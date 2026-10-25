"""Request and response schemas for the journal, the taste page and the favourite resolver."""

import datetime as dt
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.api.v1.schemas.feed import FeedItemOut, States
from app.api.v1.schemas.profiles import FavouriteOut
from app.application.services.journal import EntryView, LinkView
from app.application.services.taste_profile import TasteMap, TasteSummary
from app.domain.journal import ENTRY_TEXT_MAX, MOOD_MAX, LinkKind, LinkSource, LinkStatus, NodeKind
from app.domain.models import FavouriteKind

EntryText = Annotated[str, StringConstraints(min_length=1, max_length=ENTRY_TEXT_MAX)]
Mood = Annotated[str, StringConstraints(strip_whitespace=True, max_length=MOOD_MAX)]


class JournalTargetOut(BaseModel):
    """The item or place a link points to. A song's `creator` is its artist."""

    node_id: UUID
    kind: NodeKind
    title: str
    year: int | None
    qloo_id: str | None
    creator: str | None
    image_url: str | None


class JournalLinkOut(BaseModel):
    """A link from an entry to an item or place."""

    id: UUID
    target: JournalTargetOut
    kind: LinkKind
    source: LinkSource
    status: LinkStatus
    reason: str

    @classmethod
    def from_view(cls, view: LinkView) -> Self:
        """Build from a link and its target."""
        node = view.target
        return cls(
            id=view.link.id,
            target=JournalTargetOut(
                node_id=node.id,
                kind=node.kind,
                title=node.title,
                year=node.year,
                qloo_id=node.qloo_id,
                creator=node.creator,
                image_url=node.image_url,
            ),
            kind=view.link.kind,
            source=view.link.source,
            status=view.link.status,
            reason=view.link.reason,
        )


class JournalEntryOut(BaseModel):
    """An entry with its confirmed links and open suggestions. `link_run_id` is set when the
    agent has just started suggesting links: poll it, then get the entry again."""

    id: UUID
    date: dt.date
    text: str
    mood: str | None
    links: list[JournalLinkOut]
    suggestions: list[JournalLinkOut]
    link_run_id: UUID | None
    created_at: dt.datetime
    updated_at: dt.datetime

    @classmethod
    def from_view(cls, view: EntryView) -> Self:
        """Build from an entry view."""
        entry = view.entry
        return cls(
            id=entry.id,
            date=entry.date or entry.created_at.date(),
            text=entry.body or "",
            mood=entry.mood,
            links=[JournalLinkOut.from_view(link) for link in view.links],
            suggestions=[JournalLinkOut.from_view(link) for link in view.suggestions],
            link_run_id=view.link_run_id,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )


class JournalEntryCreate(BaseModel):
    """A new entry. The date defaults to today."""

    text: EntryText
    date: dt.date | None = None
    mood: Mood | None = None


class JournalEntryUpdate(BaseModel):
    """Fields to change. New text starts a new link run; `mood: null` clears the mood."""

    text: EntryText | None = None
    date: dt.date | None = None
    mood: Mood | None = None


class LinkDecision(BaseModel):
    """Confirm or reject a suggestion."""

    status: Literal["confirmed", "rejected"]


class TranscriptOut(BaseModel):
    """The words in a voice note, for the user to edit before saving."""

    text: str


class TagOut(BaseModel):
    """A top tag and its weight (0–1)."""

    name: str
    weight: float


class TasteOut(BaseModel):
    """The taste page."""

    sentence: str
    top_tags: list[TagOut]
    by_type: dict[str, int]
    favourites: list[FavouriteOut]
    recent_likes: list[FeedItemOut]

    @classmethod
    def from_summary(cls, summary: TasteSummary, states: States) -> Self:
        """Build from the taste summary."""
        return cls(
            sentence=summary.sentence,
            top_tags=[TagOut(name=tag.name, weight=tag.weight) for tag in summary.top_tags],
            by_type=summary.by_type,
            favourites=[FavouriteOut.from_domain(item) for item in summary.favourites],
            recent_likes=[FeedItemOut.from_domain(item, states) for item in summary.recent_likes],
        )


class MapNodeOut(BaseModel):
    """A node on the taste map. `kind` is a type, `place` or `entry`."""

    id: str
    kind: str
    title: str
    image_url: str | None
    weight: float


class MapLinkOut(BaseModel):
    """An edge on the taste map: `because_of` or `mentions`."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    from_: str = Field(alias="from")
    to: str
    kind: str


class TasteMapOut(BaseModel):
    """The taste map, capped and with confirmed links only."""

    nodes: list[MapNodeOut]
    links: list[MapLinkOut]

    @classmethod
    def from_map(cls, taste_map: TasteMap) -> Self:
        """Build from the taste map."""
        return cls(
            nodes=[
                MapNodeOut(
                    id=node.id,
                    kind=node.kind,
                    title=node.title,
                    image_url=node.image_url,
                    weight=node.weight,
                )
                for node in taste_map.nodes
            ],
            links=[
                MapLinkOut(from_=link.source, to=link.target, kind=link.kind)
                for link in taste_map.links
            ],
        )


class ResolveIn(BaseModel):
    """What the user typed for a favourite: a name, a song, a lyric or a description. It's used
    for this lookup only and never stored."""

    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    kind: FavouriteKind | None = None
    hint: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None


class ResolveOut(BaseModel):
    """The resolve run to poll."""

    agent_run_id: UUID
