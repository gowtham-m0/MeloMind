"""Use cases for one item: its details, "More like this", an artist's songs, and the optional
YouTube preview.

For a song, "More like this" is "After this song": Qloo's artists for the song's artist, one top
song each from the song catalogue. The match is artist-level taste, and the cards say so.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from uuid import UUID

from app.application.agent.cards import candidate_from_match, candidate_from_song, to_card
from app.application.ports import (
    CatalogRepository,
    ExclusionRepository,
    FeedRepository,
    InsightsQuery,
    JournalRepository,
    MediaResolver,
    PlayableMedia,
    Song,
    SongCatalog,
    TasteGraph,
)
from app.application.services.profiles import ProfileService
from app.core.errors import NotFoundError, UpstreamError
from app.domain.feed import FeedItem, ItemSource, entity_type_of, is_qloo_ref
from app.domain.feedback import Blocklist
from app.domain.journal import NodeKind, confirmed_media
from app.domain.links import platform_links
from app.domain.models import EntityType, Profile

logger = logging.getLogger(__name__)

MORE_LIKE_THIS = 12
# Ask for a few more, so excluded items and the item itself can drop out.
MORE_LIKE_THIS_TAKE = 16
ARTIST_SONGS = 5
AFTER_SONG_ARTISTS = 8
SONGS_TIMEOUT_SECONDS = 8.0


@dataclass(frozen=True)
class ItemDetail:
    """An item with what the detail sheet shows besides the card. `songs` is an artist's own
    top songs (empty for other types)."""

    item: FeedItem
    more_like_this: list[FeedItem]
    preview_available: bool
    songs: list[FeedItem] = field(default_factory=list)


class ItemService:
    """Item details for their owner's profiles. Excluded items are not found (rule 3)."""

    def __init__(
        self,
        profiles: ProfileService,
        feeds: FeedRepository,
        catalog: CatalogRepository,
        exclusions: ExclusionRepository,
        taste: TasteGraph,
        media: MediaResolver | None = None,
        songs: SongCatalog | None = None,
        journal: JournalRepository | None = None,
    ) -> None:
        self._profiles = profiles
        self._journal = journal
        self._feeds = feeds
        self._catalog = catalog
        self._exclusions = exclusions
        self._taste = taste
        self._media = media
        self._songs = songs

    async def detail(self, owner_id: UUID, profile_id: UUID, ref: str) -> ItemDetail:
        """The item, and more like it."""
        profile = await self._profiles.get(owner_id, profile_id)
        blocklist = Blocklist.from_exclusions(await self._exclusions.list_for_profile(profile.id))
        item = await self._find(profile, ref)
        if item is None or blocklist.blocks(item.ref, item.title):
            raise NotFoundError("Item not found.")
        country = profile.country_code
        if item.entity_type is EntityType.SONG:
            more = await self._after_song(item, blocklist, country)
        else:
            more = await self._more_like_this(item, blocklist, country)
        songs = (
            await self._artist_songs(item, blocklist, country)
            if item.entity_type is EntityType.ARTIST
            else []
        )
        return ItemDetail(
            item=item,
            more_like_this=more,
            preview_available=self._media is not None and item.entity_type is not EntityType.BOOK,
            songs=songs,
        )

    async def preview(self, owner_id: UUID, profile_id: UUID, ref: str) -> PlayableMedia:
        """A YouTube video for the item, looked up only now (rule 6). Not found when there's
        no playable one: the button hides, never an unrelated video."""
        profile = await self._profiles.get(owner_id, profile_id)
        item = await self._find(profile, ref)
        if self._media is None or item is None or item.entity_type is EntityType.BOOK:
            raise NotFoundError("No preview for this item.")
        try:
            media = await self._media.resolve(preview_query(item))
        except UpstreamError:
            logger.warning("Preview lookup failed")
            raise NotFoundError("No preview right now.") from None
        if media is None:
            raise NotFoundError("No playable preview found.")
        return media

    async def _find(self, profile: Profile, ref: str) -> FeedItem | None:
        feed = await self._feeds.latest(profile.id, done_only=True)
        item = feed.find(ref) if feed else None
        if item is not None:
            return item
        known = (await self._catalog.get_many([ref])).get(ref)
        return known or await self._own_item(profile, ref)

    async def _own_item(self, profile: Profile, ref: str) -> FeedItem | None:
        """A verified favourite or a confirmed journal item, opened from the taste page or the
        journal: a plain card built from what the profile already holds."""
        if not is_qloo_ref(ref):
            return None
        source = ItemSource(self._taste.source)
        country = profile.country_code
        for favourite in profile.favourites:
            if favourite.qloo_id == ref:
                entity_type = entity_type_of(favourite.kind)
                return FeedItem(
                    ref=ref,
                    title=favourite.name,
                    entity_type=entity_type,
                    source=source,
                    reason="One of your favourites.",
                    image_url=favourite.image_url,
                    links=platform_links(favourite.name, entity_type, country_code=country),
                )
        if self._journal is None:
            return None
        nodes = await self._journal.list_nodes(profile.id)
        links = await self._journal.list_links(profile.id)
        for node, _link in confirmed_media(nodes, links):
            if node.qloo_id != ref:
                continue
            is_song = node.kind is NodeKind.SONG
            title = node.creator if is_song and node.creator else node.title
            entity_type = EntityType.ARTIST if is_song else EntityType(node.kind.value)
            return FeedItem(
                ref=ref,
                title=title,
                entity_type=entity_type,
                source=source,
                reason="From your journal.",
                year=None if is_song else node.year,
                image_url=None if is_song else node.image_url,
                links=platform_links(title, entity_type, country_code=country, year=node.year),
            )
        return None

    async def _more_like_this(
        self, item: FeedItem, blocklist: Blocklist, country_code: str | None
    ) -> list[FeedItem]:
        if not is_qloo_ref(item.ref):
            return []
        query = InsightsQuery(
            entity_type=item.entity_type,
            take=MORE_LIKE_THIS_TAKE,
            signal_entities=(item.ref,),
            exclude_entities=blocklist.qloo_ids,
        )
        try:
            matches = await self._taste.insights(query)
        except UpstreamError:
            logger.warning("More like this: Qloo failed")
            return []
        cards = [
            to_card(
                candidate_from_match(match, f"similar to {item.title}", item.ref, item.title),
                country_code,
            )
            for match in matches
            if match.entity_id != item.ref and not blocklist.blocks(match.entity_id, match.name)
        ][:MORE_LIKE_THIS]
        await self._catalog.put_many(cards)
        return cards

    async def _artist_songs(
        self, item: FeedItem, blocklist: Blocklist, country_code: str | None
    ) -> list[FeedItem]:
        """The artist's own best-known songs, when there's a song catalogue."""
        if self._songs is None or not is_qloo_ref(item.ref):
            return []
        found = await self._lookup(item.title, country_code, ARTIST_SONGS)
        cards = [
            to_card(
                candidate_from_song(
                    song,
                    artist_ref=item.ref,
                    artist_name=item.title,
                    signal=f"a top song by {item.title}",
                    because_ref=item.ref,
                    because_name=item.title,
                ),
                country_code,
            )
            for song in found
        ]
        cards = [card for card in cards if not blocklist.blocks(card.ref, card.title)]
        await self._catalog.put_many(cards)
        return cards

    async def _after_song(
        self, item: FeedItem, blocklist: Blocklist, country_code: str | None
    ) -> list[FeedItem]:
        """Qloo's artists for the song's artist, with a top song each."""
        parent = item.parent_ref
        if self._songs is None or not parent or not is_qloo_ref(parent):
            return []
        query = InsightsQuery(
            entity_type=EntityType.ARTIST,
            take=AFTER_SONG_ARTISTS + 4,
            signal_entities=(parent,),
            exclude_entities=blocklist.qloo_ids,
        )
        try:
            artists = await self._taste.insights(query)
        except UpstreamError:
            logger.warning("After this song: Qloo failed")
            return []
        artists = [
            artist
            for artist in artists
            if artist.entity_id != parent and not blocklist.blocks(artist.entity_id, artist.name)
        ][:AFTER_SONG_ARTISTS]
        try:
            found = await asyncio.wait_for(
                asyncio.gather(*(self._lookup(a.name, country_code, 1) for a in artists)),
                SONGS_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            return []
        source = item.parent_title or item.creator or item.title
        cards = [
            to_card(
                candidate_from_song(
                    songs[0],
                    artist_ref=artist.entity_id,
                    artist_name=artist.name,
                    signal=f"a top song by {artist.name}, whose fans Qloo matches to {source}",
                    because_ref=parent,
                    because_name=source,
                ),
                country_code,
            )
            for artist, songs in zip(artists, found, strict=True)
            if songs
        ]
        cards = [
            card
            for card in cards
            if card.ref != item.ref and not blocklist.blocks(card.ref, card.title)
        ][:MORE_LIKE_THIS]
        await self._catalog.put_many(cards)
        return cards

    async def _lookup(self, artist: str, country_code: str | None, take: int) -> list[Song]:
        if self._songs is None:
            return []
        try:
            return await self._songs.top_songs(artist, country_code, take)
        except UpstreamError:
            logger.warning("Song catalogue failed")
            return []


def preview_query(item: FeedItem) -> str:
    """What to search on YouTube: an artist's music video, a song's official audio, or a film's
    or show's trailer."""
    if item.entity_type is EntityType.ARTIST:
        return f"{item.title} official music video"
    if item.entity_type is EntityType.SONG:
        artist = item.creator or ""
        return f"{artist} {item.title} official audio".strip()
    year = f" {item.year}" if item.year else ""
    return f"{item.title}{year} official trailer"
