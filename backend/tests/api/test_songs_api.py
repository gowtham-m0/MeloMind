"""API tests for songs: the songs row, a song's "After this song", an artist's own songs, and
signals on a song reaching its artist. The song catalogue is a fake; nothing calls Apple."""

import asyncio
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.auth import SupabaseTokenVerifier
from app.api.deps import Adapters, get_container, memory_adapters, wire
from app.domain.feed import FeedItem, ItemSource
from app.domain.feedback import Blocklist, Exclusion
from app.domain.models import EntityType
from app.infrastructure.qloo.demo_profiles import load_demo_profiles
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from app.main import create_app
from tests.conftest import AuthHeaders, make_settings
from tests.fakes import FakeSongCatalog, InlineRunner

API = "/api/v1"


@pytest.fixture
def adapters() -> Adapters:
    """In-memory adapters with a (fake) song catalogue."""
    return memory_adapters(FixtureTasteGraph(), songs=FakeSongCatalog())


@pytest.fixture
def songs_client(verifier: SupabaseTokenVerifier, adapters: Adapters) -> Iterator[TestClient]:
    """An API client whose container has a (fake) song catalogue."""
    container = wire(
        adapters,
        verifier,
        load_demo_profiles(),
        make_settings(),
        InlineRunner(),
    )
    app = create_app(make_settings())
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client


def leo_feed(client: TestClient, headers: dict[str, str]) -> tuple[str, dict[str, Any]]:
    profile_id = client.post(f"{API}/demo/seed", headers=headers).json()["profile_ids"][1]
    response = client.get(f"{API}/profiles/{profile_id}/feed", headers=headers)
    assert response.status_code == 200, response.text
    return profile_id, response.json()


def songs_row(feed: dict[str, Any]) -> dict[str, Any]:
    return next(row for row in feed["rows"] if row["key"] == "songs")


def test_the_feed_has_a_songs_row_with_previews_and_apple_music_first(
    songs_client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    _, feed = leo_feed(songs_client, auth(user_id))

    row = songs_row(feed)
    song = row["items"][0]
    assert song["entity_type"] == "song"
    assert song["creator"]
    assert song["preview_url"].startswith("https://")
    assert song["image_aspect"] == "square"
    assert song["links"][0]["label"] == "Listen on Apple Music"
    assert "courtesy of iTunes" in row["subtitle"]


def test_a_song_opens_with_songs_by_artists_qloo_matches(
    songs_client: TestClient, adapters: Adapters, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id, _ = leo_feed(songs_client, headers)
    # The demo fixtures only relate favourites, so use a song of one (Leo's The Supremes).
    song = FeedItem(
        ref="song:supremes-1",
        title="Baby Love",
        entity_type=EntityType.SONG,
        source=ItemSource.SONG_CATALOGUE,
        reason="A top song by The Supremes.",
        creator="The Supremes",
        parent_ref="demo-artist-the-supremes",
        parent_title="The Supremes",
    )
    asyncio.run(adapters.catalog.put_many([song]))

    detail = songs_client.get(f"{API}/profiles/{profile_id}/items/{song.ref}", headers=headers)

    assert detail.status_code == 200, detail.text
    after = detail.json()["more_like_this"]
    assert after
    assert all(item["entity_type"] == "song" for item in after)
    assert all("Qloo matches to The Supremes" in item["reason"] for item in after)
    assert all(item["because_of"]["title"] == "The Supremes" for item in after)
    assert "The Supremes" not in {item["creator"] for item in after}


def test_an_artist_opens_with_their_own_songs(
    songs_client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id, feed = leo_feed(songs_client, headers)
    artist = next(
        item for row in feed["rows"] for item in row["items"] if item["entity_type"] == "artist"
    )

    detail = songs_client.get(
        f"{API}/profiles/{profile_id}/items/{artist['ref']}", headers=headers
    ).json()

    assert detail["songs"]
    assert all(song["creator"] == artist["title"] for song in detail["songs"])


def test_liking_a_song_also_likes_its_artist(
    songs_client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id, feed = leo_feed(songs_client, headers)
    song = songs_row(feed)["items"][0]

    response = songs_client.post(
        f"{API}/profiles/{profile_id}/feedback",
        json={
            "ref": song["ref"],
            "title": song["title"],
            "entity_type": "song",
            "signal": "liked",
        },
        headers=headers,
    )
    library = songs_client.get(f"{API}/profiles/{profile_id}/library", headers=headers).json()

    assert response.status_code == 200, response.text
    liked = {item["ref"]: item for item in library["liked"]}
    assert song["ref"] in liked
    assert any(item["entity_type"] == "artist" for item in liked.values())


def test_dismissing_a_song_does_not_dismiss_its_artist(
    songs_client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id, feed = leo_feed(songs_client, headers)
    song = songs_row(feed)["items"][0]

    songs_client.post(
        f"{API}/profiles/{profile_id}/feedback",
        json={"ref": song["ref"], "title": song["title"], "signal": "not_interested"},
        headers=headers,
    )
    exclusions = songs_client.get(f"{API}/profiles/{profile_id}/exclusions", headers=headers).json()

    assert [entry["entity_ref"] for entry in exclusions] == [song["ref"]]


def test_excluded_songs_never_reach_qloo(user_id: UUID) -> None:
    blocklist = Blocklist.from_exclusions(
        [
            Exclusion(user_id, "song:123", "Paper Moons"),
            Exclusion(user_id, "fav:abc", "Typed Favourite"),
            Exclusion(user_id, "QLOO-ARTIST-1", "The Lanterns"),
        ]
    )

    assert blocklist.qloo_ids == ("QLOO-ARTIST-1",)
