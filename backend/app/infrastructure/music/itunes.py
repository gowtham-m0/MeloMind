"""`SongCatalog` over Apple's iTunes Search API (`/search`, no key).

Apple's terms for the Search API (its "Legal" section) shape how songs are used:
- previews and artwork are promo content: shown only to promote the song, next to a link to its
  store page, with previews credited "courtesy of iTunes";
- previews are streamed only, never downloaded, saved or cached. We keep URLs, never files;
- about 20 calls a minute are allowed, so lookups are cached in memory and spaced out.
Only the artist name Qloo returned is sent: never user text, lyrics or journal content.
"""

import asyncio
import logging
import re
import time
from collections import deque
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from app.application.ports import Song
from app.core.errors import UpstreamError
from app.domain.names import names_match, normalise_name

logger = logging.getLogger(__name__)

ITUNES_BASE_URL = "https://itunes.apple.com"
ITUNES_TIMEOUT_SECONDS = 6.0
SEARCH_LIMIT = 25
CALLS_PER_MINUTE = 18
WINDOW_SECONDS = 60.0
CACHE_SECONDS = 6 * 60 * 60
DEFAULT_STORE = "US"
ARTWORK_SIZE = "600x600bb"

_ARTWORK_THUMB = re.compile(r"\d+x\d+bb")
_CREDIT_SPLIT = re.compile(r"\s*(?:,|&|\band\b|\bx\b|\bfeat\.?|\bft\.?|\bwith\b)\s*", re.I)
_VERSION = re.compile(r"\s*[(\[][^)\]]*[)\]]")
_NOISE = re.compile(
    r"\b(karaoke|tribute|instrumental|cover version|8[- ]bit|lullaby|made famous|re-?recorded|"
    r"remix|slowed|sped up|reverb|lo-?fi)\b",
    re.I,
)


class ITunesSongCatalog:
    """Top songs for an artist from the iTunes Store, in the user's country's store."""

    def __init__(
        self, client: httpx.AsyncClient, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._client = client
        self._clock = clock
        self._cache: dict[tuple[str, str], tuple[float, list[Song]]] = {}
        self._calls: deque[float] = deque()
        self._slot = asyncio.Lock()

    async def top_songs(
        self, artist: str, country_code: str | None = None, take: int = 5
    ) -> list[Song]:
        """The artist's songs as the store ranks them, credited to them, one per title."""
        name = " ".join(artist.split())
        if not name:
            return []
        store = _store(country_code)
        key = (normalise_name(name), store)
        cached = self._cache.get(key)
        if cached is not None and self._clock() - cached[0] < CACHE_SECONDS:
            return cached[1][:take]
        await self._wait_for_slot()
        try:
            response = await self._client.get(
                "/search",
                params={
                    "term": name,
                    "media": "music",
                    "entity": "song",
                    "attribute": "artistTerm",
                    "country": store,
                    "limit": SEARCH_LIMIT,
                },
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise UpstreamError("The song catalogue didn't answer.") from error
        songs = parse_songs(data, name)
        self._cache[key] = (self._clock(), songs)
        return songs[:take]

    async def _wait_for_slot(self) -> None:
        """Keep under Apple's rate limit: at most `CALLS_PER_MINUTE` calls in any minute."""
        async with self._slot:
            now = self._clock()
            while self._calls and now - self._calls[0] >= WINDOW_SECONDS:
                self._calls.popleft()
            if len(self._calls) >= CALLS_PER_MINUTE:
                await asyncio.sleep(WINDOW_SECONDS - (now - self._calls[0]))
                self._calls.popleft()
            self._calls.append(self._clock())


def parse_songs(data: Mapping[str, Any], artist: str) -> list[Song]:
    """Songs credited to `artist`, in the store's order, without karaoke, tributes, remixes or a
    second version of the same title."""
    songs: list[Song] = []
    titles: set[str] = set()
    for raw in data.get("results") or ():
        if not isinstance(raw, Mapping) or raw.get("kind") != "song":
            continue
        title = str(raw.get("trackName") or "").strip()
        credit = str(raw.get("artistName") or "").strip()
        track_id = raw.get("trackId")
        if not title or not credit or track_id is None or not credited(credit, artist):
            continue
        if _NOISE.search(title) or _NOISE.search(str(raw.get("collectionName") or "")):
            continue
        base = normalise_name(_VERSION.sub("", title).split(" - ")[0])
        if not base or base in titles:
            continue
        titles.add(base)
        songs.append(
            Song(
                track_id=str(track_id),
                title=title,
                artist_credit=credit,
                album=_text(raw.get("collectionName")),
                year=_year(raw.get("releaseDate")),
                artwork_url=_artwork(raw.get("artworkUrl100")),
                preview_url=_https(raw.get("previewUrl")),
                store_url=_https(raw.get("trackViewUrl")),
            )
        )
    return songs


def credited(credit: str, artist: str) -> bool:
    """True when `artist` is one of the names in the credit ("A, B & C")."""
    if names_match(credit, artist):
        return True
    return any(names_match(part, artist) for part in _CREDIT_SPLIT.split(credit) if part)


def _store(country_code: str | None) -> str:
    code = (country_code or "").strip().upper()
    return code if len(code) == 2 and code.isalpha() else DEFAULT_STORE


def _text(value: object) -> str | None:
    text = str(value).strip() if isinstance(value, str) else ""
    return text or None


def _year(value: object) -> int | None:
    if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None


def _https(value: object) -> str | None:
    return value if isinstance(value, str) and value.startswith("https://") else None


def _artwork(value: object) -> str | None:
    """The artwork at a size that suits a card (the API gives a 100px thumbnail)."""
    url = _https(value)
    return _ARTWORK_THUMB.sub(ARTWORK_SIZE, url) if url else None
