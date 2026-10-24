"""Step 4b, `add_songs` (code): the "Songs for you" row.

Qloo has no songs, so the pick stays Qloo's: the artists already chosen for this feed, in feed
order. For each, the song catalogue gives their best-known songs, and the row takes a couple from
each artist in turn. The catalogue never decides what to recommend (rule 1). No catalogue, or a
catalogue failure, means no songs row; the feed carries on.
"""

import asyncio
import logging
from collections.abc import Sequence

from app.application.agent.cards import candidate_from_song
from app.application.agent.deps import FeedDeps
from app.application.agent.state import FeedState, RowDraft
from app.application.agent.types import Candidate, FeedContext
from app.application.ports import Song, SongCatalog
from app.core.errors import UpstreamError
from app.domain.models import EntityType
from app.domain.names import normalise_name

logger = logging.getLogger(__name__)

NODE = "add_songs"
ROW_KEY = "songs"
SONG_ARTISTS = 6
SONGS_PER_ARTIST = 2
SONGS_TIMEOUT_SECONDS = 8.0
MIN_SONGS = 4
# The songs row goes right after this row, so music stays together.
AFTER_ROW = "music"


async def add_songs(state: FeedState, deps: FeedDeps) -> FeedState:
    """Add the songs row when there's a catalogue and enough songs."""
    if deps.songs is None:
        return {}
    context = state["context"]
    drafts = list(state.get("drafts", []))
    artists = feed_artists(state.get("hero"), drafts, context)
    if not artists:
        return {}
    try:
        found = await asyncio.wait_for(
            _lookup_all(deps.songs, artists, context.country_code), SONGS_TIMEOUT_SECONDS
        )
    except TimeoutError:
        await deps.log.warn(NODE, "The song catalogue was too slow, so no songs row this time.")
        return {}
    picks = pick_songs(artists, found, context, deps.limits.row_size)
    names = ", ".join(artist.name for artist in artists[:3])
    if len(picks) < MIN_SONGS:
        await deps.log.info(NODE, f"Left out “Songs for you”: only {len(picks)} songs found.")
        return {}
    await deps.log.info(
        NODE,
        f"Looked up songs for {len(artists)} artists Qloo picked ({names}…) in Apple's catalogue "
        f"→ {len(picks)} songs.",
    )
    draft = RowDraft(
        key=ROW_KEY,
        title="Songs for you",
        subtitle="Top tracks from artists in your taste. Previews courtesy of iTunes",
        placement="main",
        reason=None,
        min_items=MIN_SONGS,
        candidates=picks,
    )
    keys = [existing["key"] for existing in drafts]
    position = keys.index(AFTER_ROW) + 1 if AFTER_ROW in keys else len(drafts)
    drafts.insert(position, draft)
    return {"drafts": drafts}


def feed_artists(
    hero: Candidate | None, drafts: Sequence[RowDraft], context: FeedContext
) -> list[Candidate]:
    """The first few distinct artists in the feed, hero first, in row order."""
    seen: set[str] = set()
    artists: list[Candidate] = []
    ordered = ([hero] if hero else []) + [
        candidate
        for draft in drafts
        if draft["placement"] == "main"
        for candidate in draft["candidates"]
    ]
    for candidate in ordered:
        if candidate.entity_type is not EntityType.ARTIST or candidate.entity_id in seen:
            continue
        if context.blocklist.blocks(candidate.entity_id, candidate.name):
            continue
        seen.add(candidate.entity_id)
        artists.append(candidate)
        if len(artists) == SONG_ARTISTS:
            break
    return artists


async def _lookup_all(
    catalog: SongCatalog, artists: Sequence[Candidate], country_code: str | None
) -> list[list[Song]]:
    return list(
        await asyncio.gather(*(_lookup(catalog, artist.name, country_code) for artist in artists))
    )


async def _lookup(catalog: SongCatalog, artist: str, country_code: str | None) -> list[Song]:
    try:
        return await catalog.top_songs(artist, country_code, take=SONGS_PER_ARTIST + 2)
    except UpstreamError:
        logger.warning("Song catalogue failed for one artist")
        return []


def pick_songs(
    artists: Sequence[Candidate],
    found: Sequence[Sequence[Song]],
    context: FeedContext,
    size: int,
) -> list[Candidate]:
    """Songs in turn from each artist, up to `SONGS_PER_ARTIST` each, skipping excluded songs and
    the same title twice."""
    picks: list[Candidate] = []
    titles: set[str] = set()
    taken = [0] * len(artists)
    for _ in range(SONGS_PER_ARTIST):
        for index, (artist, songs) in enumerate(zip(artists, found, strict=True)):
            for song in songs:
                if taken[index] >= SONGS_PER_ARTIST or len(picks) >= size:
                    break
                candidate = _candidate(song, artist)
                key = normalise_name(song.title)
                if key in titles or candidate.entity_id in {p.entity_id for p in picks}:
                    continue
                if context.blocklist.blocks(candidate.entity_id, candidate.name):
                    continue
                titles.add(key)
                picks.append(candidate)
                taken[index] += 1
                break
    return picks


def _candidate(song: Song, artist: Candidate) -> Candidate:
    """A song card that says why: its artist is Qloo's pick, for the artist's own reason."""
    why = " ".join(artist.signal.split()).rstrip(".")
    signal = f"a top song by {artist.name}" + (f", {why}" if why else ", picked for you by Qloo")
    return candidate_from_song(
        song,
        artist_ref=artist.entity_id,
        artist_name=artist.name,
        signal=signal,
        because_ref=artist.because_ref,
        because_name=artist.because_name,
    )
