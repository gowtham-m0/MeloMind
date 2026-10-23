"""Tests for the server-side caches: Qloo results and media lookups."""

from datetime import timedelta

import pytest

from app.application.ports import EntityMatch, InsightsQuery, PlayableMedia
from app.core.errors import UpstreamError
from app.domain.models import EntityType, utc_now
from app.infrastructure.media.cached import CachedMediaResolver, query_key
from app.infrastructure.persistence.memory_caches import InMemoryMediaCache, InMemoryQlooCache
from app.infrastructure.qloo.cached_taste_graph import CachedTasteGraph
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from tests.fakes import RecordingTasteGraph

pytestmark = pytest.mark.anyio


async def test_qloo_results_are_cached_per_request() -> None:
    recorder = RecordingTasteGraph(FixtureTasteGraph())
    graph = CachedTasteGraph(recorder, InMemoryQlooCache())
    query = InsightsQuery(EntityType.ARTIST, take=5, signal_entities=("demo-artist-the-supremes",))

    first = await graph.insights(query)
    second = await graph.insights(query)
    other = await graph.insights(
        InsightsQuery(EntityType.ARTIST, take=3, signal_entities=query.signal_entities)
    )
    await graph.search("The Beatles")
    await graph.search("the beatles")

    assert first == second
    assert len(other) == 3
    assert len(recorder.insights_queries) == 2
    assert recorder.searches == ["The Beatles"]
    assert graph.source == "demo_fixture"
    assert all(isinstance(match, EntityMatch) for match in second)


async def test_stale_qloo_results_are_fetched_again() -> None:
    recorder = RecordingTasteGraph(FixtureTasteGraph())
    graph = CachedTasteGraph(recorder, InMemoryQlooCache(), ttl=timedelta(seconds=-1))

    await graph.search("The Beatles")
    await graph.search("The Beatles")

    assert len(recorder.searches) == 2


class CountingMedia:
    def __init__(self, answer: PlayableMedia | None = None, fail: bool = False) -> None:
        self.answer = answer
        self.fail = fail
        self.calls = 0

    async def resolve(self, query: str) -> PlayableMedia | None:
        self.calls += 1
        if self.fail:
            raise UpstreamError("YouTube refused the request.")
        return self.answer


async def test_media_lookups_and_misses_are_cached() -> None:
    hit = CountingMedia(PlayableMedia("v1", "Song", 180))
    miss = CountingMedia(None)
    cache = InMemoryMediaCache()

    for _ in range(3):
        await CachedMediaResolver(hit, cache).resolve("The Supremes  1960s")
        await CachedMediaResolver(miss, cache).resolve("Nothing here")

    assert (hit.calls, miss.calls) == (1, 1)
    assert query_key("The Supremes  1960s") == "the supremes 1960s"


async def test_a_stale_miss_is_looked_up_again_but_failures_are_never_cached() -> None:
    cache = InMemoryMediaCache()
    await cache.put("nothing", None)
    retry = CountingMedia(PlayableMedia("v2", "Song", 200))
    failing = CountingMedia(fail=True)

    found = await CachedMediaResolver(retry, cache, miss_ttl=timedelta(0)).resolve("Nothing")
    with pytest.raises(UpstreamError):
        await CachedMediaResolver(failing, cache).resolve("Broken")

    assert found is not None and found.video_id == "v2"
    assert await cache.get("broken") is None
    entry = await cache.get("nothing")
    assert entry is not None and entry.cached_at <= utc_now()
