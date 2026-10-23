"""Contract tests for QlooHttpTasteGraph with httpx.MockTransport. No live calls.

Response bodies follow the shapes in docs/QLOO_NOTES.md, section 6, with invented values.
"""

from typing import Any

import httpx
import pytest

from app.application.ports import InsightsQuery
from app.core.errors import UpstreamError
from app.domain.models import EntityType
from app.infrastructure.qloo.http_taste_graph import QlooHttpTasteGraph, build_insights_params

pytestmark = pytest.mark.anyio

BASE_URL = "https://qloo.test"
API_KEY = "test-key"


class Recorder:
    """Answers each request in turn and keeps the requests for assertions."""

    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_graph(recorder: Recorder, sleeps: list[float] | None = None) -> QlooHttpTasteGraph:
    async def fake_sleep(seconds: float) -> None:
        if sleeps is not None:
            sleeps.append(seconds)

    client = httpx.AsyncClient(base_url=BASE_URL, transport=httpx.MockTransport(recorder))
    return QlooHttpTasteGraph(client, API_KEY, sleep=fake_sleep)


def search_body(*results: Any) -> dict[str, Any]:
    return {"results": list(results)}


def insights_body(*entities: Any) -> dict[str, Any]:
    return {"success": True, "results": {"entities": list(entities)}}


ARTIST = {
    "entity_id": "a1",
    "name": "Example Singer",
    "types": ["urn:entity:artist"],
    "popularity": 0.8,
    "properties": {"short_description": "x"},
}
MOVIE = {
    "entity_id": "m1",
    "name": "Example Film",
    "type": "urn:entity",
    "subtype": "urn:entity:movie",
    "popularity": 0.9,
    "properties": {"release_year": 1965},
    "query": {"affinity": 0.75, "measurements": {}},
}


async def test_search_sends_key_header_and_params() -> None:
    recorder = Recorder(httpx.Response(200, json=search_body(ARTIST)))

    matches = await make_graph(recorder).search("Example Singer", (EntityType.ARTIST,), take=4)

    request = recorder.requests[0]
    assert request.url.path == "/search"
    assert request.headers["X-Api-Key"] == API_KEY
    assert dict(request.url.params) == {
        "query": "Example Singer",
        "types": "urn:entity:artist",
        "take": "4",
    }
    assert len(matches) == 1
    match = matches[0]
    assert (match.entity_id, match.name, match.type) == ("a1", "Example Singer", EntityType.ARTIST)
    assert match.release_year is None
    assert match.source == "qloo_live"


async def test_search_parsing_is_tolerant() -> None:
    book = {
        "entity_id": "b1",
        "name": "Example Novel",
        "types": ["urn:entity:book"],
        "properties": {"publication_year": 1960},
    }
    recorder = Recorder(
        httpx.Response(
            200,
            json=search_body(
                book,
                {"entity_id": "p1", "name": "A Place", "types": ["urn:entity:place"]},
                {"name": "No ID", "types": ["urn:entity:artist"]},
                "not an object",
            ),
        )
    )

    matches = await make_graph(recorder).search("Example")

    assert [(m.entity_id, m.release_year, m.popularity) for m in matches] == [("b1", 1960, None)]


async def test_search_404_means_no_match() -> None:
    recorder = Recorder(httpx.Response(404, json={"error": "No results"}))

    assert await make_graph(recorder).search("Nobody") == []


async def test_insights_parses_subtype_year_and_affinity() -> None:
    recorder = Recorder(httpx.Response(200, json=insights_body(MOVIE)))

    matches = await make_graph(recorder).insights(InsightsQuery(EntityType.MOVIE, take=5))

    assert recorder.requests[0].url.path == "/v2/insights"
    assert len(matches) == 1
    assert matches[0].type is EntityType.MOVIE
    assert matches[0].release_year == 1965
    assert matches[0].affinity == 0.75


def test_insights_params_for_films() -> None:
    params = build_insights_params(
        InsightsQuery(
            EntityType.MOVIE,
            take=12,
            signal_entities=("e1", "e2"),
            signal_tags=("t1",),
            age_55_plus=True,
            year_min=1961,
            year_max=1969,
            country_code="IN",
            popularity_min=0.7,
            exclude_entities=("x1",),
            exclude_tags=("xt",),
            score_entities=("s1", "s2"),
        )
    )

    assert params == {
        "filter.type": "urn:entity:movie",
        "take": "12",
        "signal.interests.entities": "e1,e2",
        "signal.interests.tags": "t1",
        "signal.demographics.age": "55_and_older",
        "filter.release_year.min": "1961",
        "filter.release_year.max": "1969",
        "filter.release_country": "India",
        "filter.popularity.min": "0.7",
        "filter.exclude.entities": "x1",
        "filter.exclude.tags": "xt",
        "filter.results.entities": "s1,s2",
    }


def test_insights_params_for_books_use_publication_year_and_no_country() -> None:
    params = build_insights_params(
        InsightsQuery(EntityType.BOOK, take=5, year_min=1960, year_max=1970, country_code="US")
    )

    assert params == {
        "filter.type": "urn:entity:book",
        "take": "5",
        "filter.publication_year.min": "1960",
        "filter.publication_year.max": "1970",
    }


def test_insights_params_for_artists_drop_era_and_country() -> None:
    params = build_insights_params(
        InsightsQuery(EntityType.ARTIST, take=5, year_min=1960, year_max=1970, country_code="US")
    )

    assert params == {"filter.type": "urn:entity:artist", "take": "5"}


def test_unknown_country_code_is_dropped() -> None:
    params = build_insights_params(InsightsQuery(EntityType.MOVIE, take=5, country_code="ZZ"))

    assert "filter.release_country" not in params


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_retries_rate_limits_and_server_errors_with_backoff(status: int) -> None:
    recorder = Recorder(
        httpx.Response(status),
        httpx.Response(status),
        httpx.Response(200, json=insights_body(MOVIE)),
    )
    sleeps: list[float] = []

    matches = await make_graph(recorder, sleeps).insights(InsightsQuery(EntityType.MOVIE, take=5))

    assert len(matches) == 1
    assert len(recorder.requests) == 3
    assert sleeps == [0.5, 1.0]


async def test_retry_after_header_is_respected_up_to_a_cap() -> None:
    recorder = Recorder(
        httpx.Response(429, headers={"Retry-After": "60"}),
        httpx.Response(200, json=search_body(ARTIST)),
    )
    sleeps: list[float] = []

    await make_graph(recorder, sleeps).search("Example")

    assert sleeps == [5.0]


async def test_gives_up_after_three_attempts() -> None:
    recorder = Recorder(httpx.Response(503), httpx.Response(503), httpx.Response(503))

    with pytest.raises(UpstreamError):
        await make_graph(recorder).search("Example")
    assert len(recorder.requests) == 3


async def test_timeouts_are_retried_then_reported() -> None:
    timeout = httpx.ReadTimeout("timed out")
    recorder = Recorder(timeout, timeout, timeout)

    with pytest.raises(UpstreamError):
        await make_graph(recorder).search("Example")
    assert len(recorder.requests) == 3


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_errors_are_not_retried(status: int) -> None:
    recorder = Recorder(httpx.Response(status))

    with pytest.raises(UpstreamError):
        await make_graph(recorder).search("Example")
    assert len(recorder.requests) == 1


async def test_missing_signal_400_is_an_empty_result() -> None:
    recorder = Recorder(
        httpx.Response(400, json={"error": "at least one valid signal or filter is required"})
    )

    assert await make_graph(recorder).insights(InsightsQuery(EntityType.MOVIE, take=5)) == []


async def test_non_json_body_is_an_empty_result() -> None:
    recorder = Recorder(httpx.Response(200, text="<html>oops</html>"))

    assert await make_graph(recorder).search("Example") == []


async def test_tags_send_the_query_and_map_id_to_tag_id() -> None:
    body = {
        "success": True,
        "results": {
            "tags": [
                {"id": "urn:tag:genre:music:60s", "name": "60s", "type": "urn:tag:genre:music"},
                {"name": "no id"},
                "not a tag",
            ]
        },
    }
    recorder = Recorder(httpx.Response(200, json=body))

    tags = await make_graph(recorder).tags("60s", take=3)

    request = recorder.requests[0]
    assert request.url.path == "/v2/tags"
    assert request.url.params["filter.query"] == "60s"
    assert request.url.params["take"] == "3"
    assert [(tag.tag_id, tag.name) for tag in tags] == [("urn:tag:genre:music:60s", "60s")]


def test_insights_params_for_warmup_scoring() -> None:
    params = build_insights_params(
        InsightsQuery(
            EntityType.ARTIST,
            take=4,
            signal_entities=("chosen",),
            score_entities=("a", "b"),
            exclude_entities=("blocked",),
        )
    )

    assert params["filter.results.entities"] == "a,b"
    assert params["signal.interests.entities"] == "chosen"
    assert params["filter.exclude.entities"] == "blocked"
