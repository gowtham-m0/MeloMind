"""The taste page: your taste in a sentence, top tags, counts by type, favourites, recent likes,
and the taste map of how your likes connect.

Only confirmed journal links count (rule 4). The sentence is written from tag names and titles
only, never journal text, with a template when the LLM is off or fails.
"""

import asyncio
import logging
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.application.agent.cards import GENERIC_TAGS, tag_key
from app.application.ports import (
    CatalogRepository,
    ExclusionRepository,
    FeedbackRepository,
    JournalRepository,
    LanguageModel,
    TasteGraph,
)
from app.application.services.library import LibraryService
from app.application.services.profiles import ProfileService
from app.core.errors import UpstreamError
from app.domain.feed import FeedItem, favourite_ref, is_qloo_ref
from app.domain.feedback import Blocklist, Feedback
from app.domain.journal import (
    MEDIA_KINDS,
    JournalLink,
    JournalNode,
    LinkStatus,
    NodeKind,
    confirmed_media,
    signal_type,
)
from app.domain.models import Favourite, FavouriteKind, Profile, utc_now
from app.domain.policies import learned_weights, signal_refs

logger = logging.getLogger(__name__)

TOP_TAGS_MAX = 10
RECENT_LIKES_MAX = 12
FAVOURITE_LOOKUPS_MAX = 8
SENTENCE_TAGS = 3
SENTENCE_MAX = 160
SENTENCE_TIMEOUT_SECONDS = 15.0
SENTENCE_CACHE_MAX = 200
ENTRY_WEIGHT = 0.5

SENTENCE_SYSTEM = (
    "You write one warm sentence that sums up someone's taste in music, films, TV and books, "
    "for the top of their taste page. Start with 'You love'. Use only the tags and titles you "
    "are given, at most 20 words, no emoji, no exclamation marks.\n"
    "Example: You love moody indie rock, big-idea sci-fi and character-driven drama."
)


class SentenceOutput(BaseModel):
    """The model's answer."""

    sentence: str = Field(description="One sentence, at most 20 words.")


@dataclass(frozen=True)
class WeightedTag:
    """A tag and how strongly it shows in the user's taste (0–1)."""

    name: str
    weight: float


@dataclass(frozen=True)
class TasteSummary:
    """Everything the taste page shows above the map."""

    sentence: str
    top_tags: list[WeightedTag]
    by_type: dict[str, int]
    favourites: list[Favourite]
    recent_likes: list[FeedItem]


@dataclass(frozen=True)
class MapNode:
    """One node on the taste map."""

    id: str
    kind: str
    title: str
    image_url: str | None
    weight: float
    seen_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class MapLink:
    """One edge: `because_of` (a like and the signal behind it) or `mentions` (an entry and an
    item it mentions)."""

    source: str
    target: str
    kind: str


@dataclass(frozen=True)
class TasteMap:
    """The capped taste map."""

    nodes: list[MapNode]
    links: list[MapLink]


class TasteProfileService:
    """The taste page for its owner's profiles."""

    def __init__(
        self,
        profiles: ProfileService,
        feedback: FeedbackRepository,
        catalog: CatalogRepository,
        journal: JournalRepository,
        library: LibraryService,
        taste: TasteGraph,
        max_map_nodes: int,
        language_model: LanguageModel | None = None,
        exclusions: ExclusionRepository | None = None,
    ) -> None:
        self._exclusions = exclusions
        self._profiles = profiles
        self._feedback = feedback
        self._catalog = catalog
        self._journal = journal
        self._library = library
        self._taste = taste
        self._max_map_nodes = max_map_nodes
        self._language_model = language_model
        self._sentences: dict[tuple[str, ...], str] = {}

    async def taste(self, owner_id: UUID, profile_id: UUID) -> TasteSummary:
        """The sentence, top tags, counts by type, favourites and recent likes."""
        profile = await self._profiles.get(owner_id, profile_id)
        feedback = await self._feedback.list_for_profile(profile.id)
        weights = learned_weights(feedback)
        strong = await self._strong_refs(profile, feedback)
        known = await self._catalog.get_many(strong)
        tags = await self._top_tags(profile, strong, weights, known)
        by_type = await self._by_type(profile, strong, feedback)
        library = await self._library.library(owner_id, profile.id)
        titles = [favourite.name for favourite in profile.favourites][:4] + [
            _title(ref, feedback) for ref in strong[:3]
        ]
        sentence = await self.sentence([tag.name for tag in tags[:5]], titles)
        return TasteSummary(
            sentence=sentence,
            top_tags=tags,
            by_type=by_type,
            favourites=list(profile.favourites),
            recent_likes=library.liked[:RECENT_LIKES_MAX],
        )

    async def sentence(self, tags: Sequence[str], titles: Sequence[str]) -> str:
        """Your taste in a sentence, from tag names and titles only. The template is used when
        the LLM is off, slow, or writes something we won't show."""
        template = template_sentence(tags, titles)
        if self._language_model is None or not (tags or titles):
            return template
        key = (*tags, "|", *titles)
        if key in self._sentences:
            return self._sentences[key]
        prompt = f"Tags: {', '.join(tags) or 'none'}.\nTitles: {', '.join(titles) or 'none'}."
        try:
            answer = await asyncio.wait_for(
                self._language_model.structured(SENTENCE_SYSTEM, prompt, SentenceOutput),
                SENTENCE_TIMEOUT_SECONDS,
            )
            sentence = " ".join(answer.sentence.split())
        except Exception as exc:
            logger.warning("Taste sentence failed: %s", type(exc).__name__)
            return template
        if not sentence or len(sentence) > SENTENCE_MAX:
            return template
        if len(self._sentences) >= SENTENCE_CACHE_MAX:
            self._sentences.clear()
        self._sentences[key] = sentence
        return sentence

    async def taste_map(self, owner_id: UUID, profile_id: UUID) -> TasteMap:
        """Favourites, strong signals and confirmed journal items as nodes, with `because_of`
        and `mentions` links, capped at the most connected, then most recent."""
        profile = await self._profiles.get(owner_id, profile_id)
        feedback = await self._feedback.list_for_profile(profile.id)
        weights = learned_weights(feedback)
        nodes: dict[str, MapNode] = {}
        for favourite in profile.favourites:
            node_id = favourite_ref(favourite)
            nodes.setdefault(
                node_id,
                MapNode(
                    id=node_id,
                    kind=favourite.kind.value,
                    title=_favourite_title(favourite),
                    image_url=favourite.image_url,
                    weight=1.0,
                    seen_at=favourite.created_at,
                ),
            )
        strong = await self._strong_refs(profile, feedback)
        known = await self._catalog.get_many(strong)
        latest = {entry.item_ref: entry for entry in feedback}
        for ref in strong:
            entry = latest[ref]
            item = known.get(ref)
            nodes.setdefault(
                ref,
                MapNode(
                    id=ref,
                    kind=(entry.entity_type.value if entry.entity_type else "artist"),
                    title=entry.title,
                    image_url=item.image_url if item else None,
                    weight=min(weights.get(ref, 0.0), 1.0),
                    seen_at=entry.created_at,
                ),
            )
        links: list[MapLink] = []
        for ref in strong:
            item = known.get(ref)
            if item and item.because_of_ref and item.because_of_ref in nodes:
                links.append(MapLink(ref, item.because_of_ref, "because_of"))
        journal_nodes = await self._journal.list_nodes(profile.id)
        journal_links = await self._journal.list_links(profile.id)
        links.extend(_journal_part(nodes, journal_nodes, journal_links))
        return _cap(nodes, links, self._max_map_nodes)

    async def _strong_refs(self, profile: Profile, feedback: Sequence[Feedback]) -> list[str]:
        """Qloo refs whose signal reached the threshold, leaving out what the user dismissed
        (rule 3)."""
        refs = [ref for ref in signal_refs(feedback) if is_qloo_ref(ref)]
        if self._exclusions is None:
            return refs
        blocklist = Blocklist.from_exclusions(await self._exclusions.list_for_profile(profile.id))
        titles = {entry.item_ref: entry.title for entry in feedback}
        return [ref for ref in refs if not blocklist.blocks(ref, titles.get(ref, ""))]

    async def _top_tags(
        self,
        profile: Profile,
        strong: Sequence[str],
        weights: dict[str, float],
        known: dict[str, FeedItem],
    ) -> list[WeightedTag]:
        """Tags counted over favourites (1 each) and strong signals (their weight, up to 1)."""
        scores: defaultdict[str, float] = defaultdict(float)
        names: dict[str, str] = {}

        def add(tags: Sequence[str], weight: float) -> None:
            for tag in tags:
                key = tag_key(tag)
                if key in GENERIC_TAGS:
                    continue
                names.setdefault(key, tag)
                scores[key] += weight

        for favourite in profile.favourites[:FAVOURITE_LOOKUPS_MAX]:
            add(await self._favourite_tags(favourite), 1.0)
        for ref in strong:
            item = known.get(ref)
            if item:
                add(item.tags, min(weights.get(ref, 0.0), 1.0))
        if not scores:
            return []
        top = max(scores.values())
        ordered = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))[:TOP_TAGS_MAX]
        return [WeightedTag(names[key], round(score / top, 2)) for key, score in ordered]

    async def _favourite_tags(self, favourite: Favourite) -> tuple[str, ...]:
        """A verified favourite's tags, from taste search by its name (cached on the server)."""
        if favourite.qloo_id is None:
            return ()
        entity_type = signal_type(NodeKind(favourite.kind.value))
        try:
            matches = await self._taste.search(
                favourite.name, (entity_type,) if entity_type else (), 5
            )
        except UpstreamError:
            return ()
        match = next((m for m in matches if m.entity_id == favourite.qloo_id), None)
        return match.tags if match else ()

    async def _by_type(
        self, profile: Profile, strong: Sequence[str], feedback: Sequence[Feedback]
    ) -> dict[str, int]:
        """How many favourites, strong signals and confirmed journal items of each type."""
        counts: Counter[str] = Counter()
        counted: set[str] = set()
        for favourite in profile.favourites:
            counts[favourite.kind.value] += 1
            counted.add(favourite_ref(favourite))
        latest = {entry.item_ref: entry for entry in feedback}
        for ref in strong:
            entity_type = latest[ref].entity_type
            if ref not in counted and entity_type is not None:
                counts[entity_type.value] += 1
                counted.add(ref)
        nodes = await self._journal.list_nodes(profile.id)
        links = await self._journal.list_links(profile.id)
        for node, _link in confirmed_media(nodes, links):
            key = node.qloo_id if node.qloo_id and node.kind is not NodeKind.SONG else str(node.id)
            if key not in counted:
                counts[node.kind.value] += 1
                counted.add(key)
        return dict(counts)


def template_sentence(tags: Sequence[str], titles: Sequence[str]) -> str:
    """ "You love indie rock, science fiction and literary fiction."."""
    picks = [tag.lower() for tag in tags[:SENTENCE_TAGS]] or list(titles[:SENTENCE_TAGS])
    if not picks:
        return "Add a few favourites and MeloMind will learn your taste."
    listing = picks[0] if len(picks) == 1 else ", ".join(picks[:-1]) + " and " + picks[-1]
    return f"You love {listing}."


def _title(ref: str, feedback: Sequence[Feedback]) -> str:
    return next((entry.title for entry in reversed(feedback) if entry.item_ref == ref), ref)


def _favourite_title(favourite: Favourite) -> str:
    if favourite.kind is FavouriteKind.SONG and favourite.song_title:
        return f"{favourite.song_title} · {favourite.name}"
    return favourite.name


def _journal_part(
    nodes: dict[str, MapNode], journal_nodes: list[JournalNode], journal_links: list[JournalLink]
) -> list[MapLink]:
    """Confirmed journal items and their entries, joined by `mentions` links. A media item Qloo
    knows shares its node with the same favourite or like."""
    by_id = {node.id: node for node in journal_nodes}
    links: list[MapLink] = []
    for link in journal_links:
        entry = by_id.get(link.from_id)
        target = by_id.get(link.to_id)
        if link.status is not LinkStatus.CONFIRMED or entry is None or target is None:
            continue
        if entry.kind is not NodeKind.ENTRY:
            continue
        entry_id = f"entry:{entry.id}"
        nodes.setdefault(
            entry_id,
            MapNode(
                id=entry_id,
                kind=NodeKind.ENTRY.value,
                title=entry.date.strftime("%d %b %Y") if entry.date else "Journal entry",
                image_url=None,
                weight=ENTRY_WEIGHT,
                seen_at=entry.created_at,
            ),
        )
        uses_qloo = target.kind in MEDIA_KINDS and target.kind is not NodeKind.SONG
        target_id = target.qloo_id if uses_qloo and target.qloo_id else f"journal:{target.id}"
        known = nodes.get(target_id)
        if known is None:
            nodes[target_id] = MapNode(
                id=target_id,
                kind=target.kind.value,
                title=target.title,
                image_url=target.image_url,
                weight=1.0,
                seen_at=link.created_at,
            )
        elif known.image_url is None and target.image_url:
            nodes[target_id] = replace(known, image_url=target.image_url)
        links.append(MapLink(entry_id, target_id, "mentions"))
    return links


def _cap(nodes: dict[str, MapNode], links: list[MapLink], limit: int) -> TasteMap:
    """The most connected nodes, then the most recent, up to the limit, and the links between
    the nodes kept."""
    unique = list(dict.fromkeys(links))
    degree: Counter[str] = Counter()
    for link in unique:
        degree[link.source] += 1
        degree[link.target] += 1
    ordered = sorted(nodes.values(), key=lambda node: (-degree[node.id], -node.seen_at.timestamp()))
    kept = ordered[:limit]
    ids = {node.id for node in kept}
    return TasteMap(
        nodes=kept,
        links=[link for link in unique if link.source in ids and link.target in ids],
    )
