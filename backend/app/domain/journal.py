"""The journal: entries, the things they mention, and the links between them.

Both are nodes. An entry node holds the text; a media node (artist, song, film, show, book) or a
place node is shared by every entry that links to it. Only confirmed links count anywhere
(rule 4): suggested ones wait for the user, and rejected ones are never suggested again.
"""

import datetime as dt
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.models import EntityType, utc_now
from app.domain.names import normalise_name

ENTRY_TEXT_MAX = 5000
MOOD_MAX = 30


class NodeKind(StrEnum):
    """What a journal node is."""

    ENTRY = "entry"
    ARTIST = "artist"
    SONG = "song"
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    BOOK = "book"
    PLACE = "place"


MEDIA_KINDS = frozenset(
    {NodeKind.ARTIST, NodeKind.SONG, NodeKind.MOVIE, NodeKind.TV_SHOW, NodeKind.BOOK}
)


class LinkKind(StrEnum):
    """How two nodes are related."""

    MENTIONS = "mentions"
    BECAUSE_OF = "because_of"
    LIKED = "liked"
    RELATED = "related"


class LinkSource(StrEnum):
    """Who made the link."""

    USER = "user"
    AGENT = "agent"
    QLOO = "qloo"
    FEED = "feed"


class LinkStatus(StrEnum):
    """Whether the user has decided on the link yet."""

    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


def signal_type(kind: NodeKind) -> EntityType | None:
    """The Qloo type a media node steers the feed as. A song steers as its artist (Qloo has no
    songs); entries and places don't steer at all."""
    if kind is NodeKind.SONG:
        return EntityType.ARTIST
    if kind in MEDIA_KINDS:
        return EntityType(kind.value)
    return None


@dataclass
class JournalNode:
    """An entry, a media item or a place.

    - Entries use `body` (the text), `date` and `mood`.
    - Media nodes use `qloo_id` when Qloo knows them. A song's `qloo_id` is its artist's, and
      `creator` names that artist.
    - `image_url` is a URL only (rule 13).
    """

    profile_id: UUID
    kind: NodeKind
    title: str
    body: str | None = None
    date: dt.date | None = None
    mood: str | None = None
    year: int | None = None
    qloo_id: str | None = None
    creator: str | None = None
    image_url: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: dt.datetime = field(default_factory=utc_now)
    updated_at: dt.datetime = field(default_factory=utc_now)

    def same_item(self, kind: NodeKind, title: str, qloo_id: str | None) -> bool:
        """True when this node already stands for that item: the same Qloo ID, or the same kind
        and title for items Qloo doesn't know. A song is matched by title, never just by its
        artist's ID."""
        if self.kind is not kind:
            return False
        if qloo_id and self.qloo_id and kind is not NodeKind.SONG:
            return self.qloo_id == qloo_id
        return normalise_name(self.title) == normalise_name(title)


@dataclass
class JournalLink:
    """A link between two nodes, usually an entry that mentions an item."""

    profile_id: UUID
    from_id: UUID
    to_id: UUID
    kind: LinkKind = LinkKind.MENTIONS
    source: LinkSource = LinkSource.AGENT
    status: LinkStatus = LinkStatus.SUGGESTED
    reason: str = ""
    id: UUID = field(default_factory=uuid4)
    created_at: dt.datetime = field(default_factory=utc_now)


def confirmed_media(
    nodes: list[JournalNode], links: list[JournalLink]
) -> list[tuple[JournalNode, JournalLink]]:
    """Media nodes the user confirmed, each with its newest confirmed link, newest first. Only
    confirmed links count (rule 4): suggested and rejected ones are ignored."""
    by_id = {node.id: node for node in nodes}
    newest: dict[UUID, JournalLink] = {}
    for link in links:
        target = by_id.get(link.to_id)
        if link.status is not LinkStatus.CONFIRMED or target is None:
            continue
        if target.kind not in MEDIA_KINDS:
            continue
        if target.id not in newest or link.created_at > newest[target.id].created_at:
            newest[target.id] = link
    pairs = [(by_id[node_id], link) for node_id, link in newest.items()]
    return sorted(pairs, key=lambda pair: pair[1].created_at, reverse=True)
