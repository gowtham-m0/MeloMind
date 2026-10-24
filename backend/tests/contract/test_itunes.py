"""Contract tests for ITunesSongCatalog with httpx.MockTransport. No live calls.

Bodies follow the iTunes Search API's result shape, with invented values.
"""

from typing import Any

import httpx
import pytest

from app.core.errors import UpstreamError
from app.infrastructure.music.itunes import ITunesSongCatalog, credited, parse_songs

pytestmark = pytest.mark.anyio

BASE_URL = "https://itunes.test"


def track(
    track_id: int,
    title: str,
    artist: str = "The Lanterns",
    album: str = "First Light",
    kind: str = "song",
) -> dict[str, Any]:
    return {
        "wrapperType": "track",
        "kind": kind,
        "trackId": track_id,
        "trackName": title,
        "artistName": artist,
        "collectionName": album,
        "releaseDate": "2013-09-09T07:00:00Z",
        "artworkUrl100": "https://is1.example/image/thumb/abc/100x100bb.jpg",
        "previewUrl": "https://audio.example/preview.m4a",
        "trackViewUrl": f"https://music.apple.com/us/album/first-light/1?i={track_id}",
    }


def catalog(body: Any, status: int = 200) -> tuple[ITunesSongCatalog, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, json=body)

    client = httpx.AsyncClient(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return ITunesSongCatalog(client), requests


async def test_it_asks_for_the_artists_songs_in_the_users_store() -> None:
    songs, requests = catalog({"results": [track(1, "Paper Moons")]})

    found = await songs.top_songs("The Lanterns", "in", take=3)

    params = requests[0].url.params
    assert requests[0].url.path == "/search"
    assert params["term"] == "The Lanterns"
    assert params["entity"] == "song"
    assert params["attribute"] == "artistTerm"
    assert params["country"] == "IN"
    assert [song.title for song in found] == ["Paper Moons"]


async def test_an_unknown_country_uses_the_us_store() -> None:
    songs, requests = catalog({"results": []})

    await songs.top_songs("The Lanterns", None)

    assert requests[0].url.params["country"] == "US"


def test_parsing_keeps_only_songs_credited_to_the_artist() -> None:
    body = {
        "results": [
            track(1, "Paper Moons"),
            track(2, "Glass Rivers", artist="Mira Vale & The Lanterns"),
            track(3, "Somebody Else", artist="The Lantern Bearers"),
            track(4, "A Music Video", kind="music-video"),
            track(5, "Paper Moons (Karaoke Version)", album="Sing Along Hits"),
            track(6, "Paper Moons (Live)"),
            track(7, "Glass Rivers (Remix)", album="Glass Rivers (Remix) - Single"),
        ]
    }

    found = parse_songs(body, "The Lanterns")

    assert [song.title for song in found] == ["Paper Moons", "Glass Rivers"]
    first = found[0]
    assert first.track_id == "1"
    assert first.year == 2013
    assert first.artwork_url == "https://is1.example/image/thumb/abc/600x600bb.jpg"
    assert first.preview_url == "https://audio.example/preview.m4a"
    assert first.store_url is not None and first.store_url.startswith("https://music.apple.com/")


def test_parsing_drops_urls_that_are_not_https() -> None:
    raw = track(1, "Paper Moons")
    raw["previewUrl"] = "http://audio.example/preview.m4a"

    found = parse_songs({"results": [raw]}, "The Lanterns")

    assert found[0].preview_url is None


@pytest.mark.parametrize(
    ("credit", "expected"),
    [
        ("Arijit Singh", True),
        ("Arijit Singh & Shreya Ghoshal", True),
        ("A.R. Rahman, Arijit Singh & Chinmayi", True),
        ("Pritam feat. Arijit Singh", True),
        ("Arijit Singh Tribute Band", False),
        ("Sonu Nigam", False),
    ],
)
def test_credit_matching(credit: str, expected: bool) -> None:
    assert credited(credit, "Arijit Singh") is expected


async def test_a_second_lookup_is_served_from_the_cache() -> None:
    songs, requests = catalog({"results": [track(1, "Paper Moons")]})

    await songs.top_songs("The Lanterns", "US")
    again = await songs.top_songs("the lanterns", "US")

    assert len(requests) == 1
    assert again[0].title == "Paper Moons"


async def test_a_failing_catalogue_raises_upstream_error() -> None:
    songs, _ = catalog({"error": "busy"}, status=503)

    with pytest.raises(UpstreamError):
        await songs.top_songs("The Lanterns", "US")


async def test_a_blank_artist_asks_nothing() -> None:
    songs, requests = catalog({"results": []})

    assert await songs.top_songs("   ") == []
    assert requests == []
