"""Contract tests for YouTubeMediaResolver with httpx.MockTransport. No live calls.

Bodies follow the YouTube Data API v3 shapes for `search` and `videos.list`, with invented values.
"""

from typing import Any

import httpx
import pytest

from app.core.errors import UpstreamError
from app.infrastructure.media.youtube import YouTubeMediaResolver, parse_duration

pytestmark = pytest.mark.anyio

BASE_URL = "https://youtube.test/v3"


def video(video_id: str, duration: str, embeddable: bool = True, privacy: str = "public") -> Any:
    return {
        "id": video_id,
        "status": {"embeddable": embeddable, "privacyStatus": privacy},
        "contentDetails": {"duration": duration},
        "snippet": {"title": f"Song &amp; {video_id}"},
    }


def resolver(handler: Any) -> tuple[YouTubeMediaResolver, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    async def no_sleep(seconds: float) -> None:
        return None

    client = httpx.AsyncClient(base_url=BASE_URL, transport=httpx.MockTransport(record))
    return YouTubeMediaResolver(client, "test-key", sleep=no_sleep), requests


def answers(search: Any, videos: Any) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        body = search if request.url.path.endswith("/search") else videos
        return httpx.Response(200, json=body)

    return handler


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("PT3M12S", 192),
        ("PT1H", 3600),
        ("PT45S", 45),
        ("P1DT1M", 86460),
        ("bad", None),
        ("P", None),
    ],
)
def test_parse_duration(text: str, seconds: int | None) -> None:
    assert parse_duration(text) == seconds


async def test_the_first_embeddable_public_video_of_a_good_length_wins() -> None:
    search = {"items": [{"id": {"videoId": v}} for v in ("hidden", "private", "long", "good")]}
    videos = {
        "items": [
            video("good", "PT3M5S"),
            video("hidden", "PT3M", embeddable=False),
            video("private", "PT3M", privacy="unlisted"),
            video("long", "PT45M"),
        ]
    }
    youtube, requests = resolver(answers(search, videos))

    media = await youtube.resolve("The Supremes 1960s hit song")

    assert media is not None
    assert (media.video_id, media.duration_s, media.provider) == ("good", 185, "youtube")
    assert media.title == "Song & good"
    search_params = requests[0].url.params
    assert search_params["videoEmbeddable"] == "true"
    assert search_params["type"] == "video"
    assert "key" not in search_params
    assert requests[0].headers["X-Goog-Api-Key"] == "test-key"
    assert requests[1].url.params["id"] == "hidden,private,long,good"
    assert "status" in requests[1].url.params["part"]


async def test_nothing_playable_is_none_never_an_unrelated_video() -> None:
    search = {"items": [{"id": {"videoId": "a"}}]}
    youtube, _ = resolver(answers(search, {"items": [video("a", "PT2M", embeddable=False)]}))

    assert await youtube.resolve("A rare song") is None


async def test_no_search_results_skip_the_videos_call() -> None:
    youtube, requests = resolver(answers({"items": []}, {"items": []}))

    assert await youtube.resolve("Nothing") is None
    assert len(requests) == 1


async def test_quota_errors_raise_so_they_are_never_cached() -> None:
    youtube, _ = resolver(lambda request: httpx.Response(403, json={"error": {}}))

    with pytest.raises(UpstreamError):
        await youtube.resolve("The Supremes")


async def test_too_many_requests_are_retried_then_reported() -> None:
    youtube, requests = resolver(lambda request: httpx.Response(429))

    with pytest.raises(UpstreamError):
        await youtube.resolve("The Supremes")
    assert len(requests) == 3


async def test_a_brief_429_recovers() -> None:
    calls = iter([httpx.Response(429), httpx.Response(200, json={"items": []})])
    youtube, requests = resolver(lambda request: next(calls))

    assert await youtube.resolve("The Supremes") is None
    assert len(requests) == 2


async def test_after_a_refusal_it_pauses_instead_of_asking_again() -> None:
    youtube, requests = resolver(lambda request: httpx.Response(403))

    with pytest.raises(UpstreamError):
        await youtube.resolve("The Supremes")
    with pytest.raises(UpstreamError):
        await youtube.resolve("The Temptations")

    assert len(requests) == 1
