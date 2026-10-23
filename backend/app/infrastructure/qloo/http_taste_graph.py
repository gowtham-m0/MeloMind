"""`TasteGraph` over the live Qloo hackathon API. Response shapes: docs/QLOO_NOTES.md, section 6."""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from app.application.ports import EntityMatch, InsightsQuery, TagMatch, TasteSource
from app.core.errors import UpstreamError
from app.domain.models import EntityType
from app.infrastructure.qloo.countries import country_name
from app.infrastructure.qloo.urns import (
    COUNTRY_FILTER_TYPES,
    PUBLICATION_YEAR_TYPES,
    RELEASE_YEAR_TYPES,
    TYPE_BY_URN,
    URN_BY_TYPE,
)

logger = logging.getLogger(__name__)

QLOO_TIMEOUT_SECONDS = 10.0
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 0.5
MAX_RETRY_AFTER_SECONDS = 5.0
AGE_55_AND_OLDER = "55_and_older"

Sleep = Callable[[float], Awaitable[None]]


def build_insights_params(query: InsightsQuery) -> dict[str, str]:
    """GET parameters for `/v2/insights`. Only parameters Qloo supports for the type are sent."""
    entity_type = query.entity_type
    params: dict[str, str] = {"filter.type": URN_BY_TYPE[entity_type], "take": str(query.take)}
    _put_list(params, "signal.interests.entities", query.signal_entities)
    _put_list(params, "signal.interests.tags", query.signal_tags)
    if query.age_55_plus:
        params["signal.demographics.age"] = AGE_55_AND_OLDER
    year_key = _year_filter_key(entity_type)
    if year_key and query.year_min is not None:
        params[f"{year_key}.min"] = str(query.year_min)
    if year_key and query.year_max is not None:
        params[f"{year_key}.max"] = str(query.year_max)
    if query.country_code and entity_type in COUNTRY_FILTER_TYPES:
        name = country_name(query.country_code)
        if name:
            params["filter.release_country"] = name
        else:
            logger.warning(
                "No Qloo country name for %s; country filter skipped", query.country_code
            )
    if query.popularity_min is not None:
        params["filter.popularity.min"] = str(query.popularity_min)
    _put_list(params, "filter.exclude.entities", query.exclude_entities)
    _put_list(params, "filter.exclude.tags", query.exclude_tags)
    _put_list(params, "filter.results.entities", query.score_entities)
    return params


def _put_list(params: dict[str, str], key: str, values: tuple[str, ...]) -> None:
    if values:
        params[key] = ",".join(values)


def _year_filter_key(entity_type: EntityType) -> str | None:
    if entity_type in RELEASE_YEAR_TYPES:
        return "filter.release_year"
    if entity_type in PUBLICATION_YEAR_TYPES:
        return "filter.publication_year"
    return None


def parse_entity(raw: Any) -> EntityMatch | None:
    """One `/search` or `/v2/insights` result, or None when it's malformed or of a type we skip."""
    if not isinstance(raw, Mapping):
        return None
    entity_id, name = raw.get("entity_id"), raw.get("name")
    entity_type = _entity_type(raw)
    if not isinstance(entity_id, str) or not isinstance(name, str) or entity_type is None:
        return None
    properties = raw.get("properties")
    properties = properties if isinstance(properties, Mapping) else {}
    query = raw.get("query")
    query = query if isinstance(query, Mapping) else {}
    return EntityMatch(
        entity_id=entity_id,
        name=name,
        type=entity_type,
        source="qloo_live",
        release_year=_as_int(properties.get("release_year"))
        or _as_int(properties.get("publication_year")),
        popularity=_as_float(raw.get("popularity")),
        affinity=_as_float(query.get("affinity")),
    )


def parse_tag(raw: Any) -> TagMatch | None:
    """One `/v2/tags` result, or None when it's malformed."""
    if not isinstance(raw, Mapping):
        return None
    tag_id, name = raw.get("id"), raw.get("name")
    if not isinstance(tag_id, str) or not isinstance(name, str):
        return None
    return TagMatch(tag_id=tag_id, name=name)


def _entity_type(raw: Mapping[str, Any]) -> EntityType | None:
    # Insights put the real type in `subtype`; search lists it in `types`.
    urns = [raw.get("subtype"), raw.get("type")]
    types = raw.get("types")
    if isinstance(types, list):
        urns.extend(types)
    return next(
        (TYPE_BY_URN[urn] for urn in urns if isinstance(urn, str) and urn in TYPE_BY_URN), None
    )


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


class QlooHttpTasteGraph:
    """Calls Qloo with the hackathon key, retrying rate limits and server errors with backoff."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        *,
        sleep: Sleep = asyncio.sleep,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._sleep = sleep
        self._max_attempts = max_attempts

    @property
    def source(self) -> TasteSource:
        """Results come from live Qloo."""
        return "qloo_live"

    async def search(
        self, query: str, types: tuple[EntityType, ...] = (), take: int = 5
    ) -> list[EntityMatch]:
        """`GET /search`. A 404 means no match."""
        params = {"query": query, "take": str(take)}
        if types:
            params["types"] = ",".join(URN_BY_TYPE[entity_type] for entity_type in types)
        body = await self._get("/search", params)
        results = body.get("results")
        matches = self._parse_all(results if isinstance(results, list) else [])
        return [match for match in matches if not types or match.type in types]

    async def insights(self, query: InsightsQuery) -> list[EntityMatch]:
        """`GET /v2/insights` for one entity type."""
        body = await self._get("/v2/insights", build_insights_params(query))
        results = body.get("results")
        entities = results.get("entities") if isinstance(results, Mapping) else None
        matches = self._parse_all(entities if isinstance(entities, list) else [])
        return [match for match in matches if match.type is query.entity_type]

    async def tags(self, query: str, take: int = 5) -> list[TagMatch]:
        """`GET /v2/tags`. Qloo's tag ID field is `id`."""
        body = await self._get("/v2/tags", {"filter.query": query, "take": str(take)})
        results = body.get("results")
        rows = results.get("tags") if isinstance(results, Mapping) else None
        tags = [parse_tag(row) for row in (rows if isinstance(rows, list) else [])]
        return [tag for tag in tags if tag is not None]

    @staticmethod
    def _parse_all(rows: list[Any]) -> list[EntityMatch]:
        matches = [parse_entity(row) for row in rows]
        skipped = matches.count(None)
        if skipped:
            logger.info("Skipped %d Qloo results that were malformed or of another type", skipped)
        return [match for match in matches if match is not None]

    async def _get(self, path: str, params: Mapping[str, str]) -> Mapping[str, Any]:
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.get(
                    path, params=params, headers={"X-Api-Key": self._api_key}
                )
            except httpx.TransportError as exc:
                logger.warning("Qloo %s attempt %d failed: %s", path, attempt, type(exc).__name__)
                if attempt == self._max_attempts:
                    raise UpstreamError("Qloo didn't respond. Please try again.") from exc
                await self._sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                logger.warning("Qloo %s attempt %d: HTTP %d", path, attempt, response.status_code)
                if attempt == self._max_attempts:
                    raise UpstreamError("Qloo is busy right now. Please try again.")
                await self._sleep(_retry_delay(response, attempt))
                continue
            return self._read(path, response)
        raise UpstreamError("Qloo didn't respond. Please try again.")

    @staticmethod
    def _read(path: str, response: httpx.Response) -> Mapping[str, Any]:
        status = response.status_code
        if status in (400, 404):
            # 404 is "no results"; 400 is usually "at least one valid signal or filter is
            # required". Both are an empty result, so the caller moves on to its next query.
            logger.info("Qloo %s: HTTP %d, treated as no results", path, status)
            return {}
        if status in (401, 403):
            logger.error(
                "Qloo %s: HTTP %d. Check QLOO_API_KEY, QLOO_BASE_URL and the type", path, status
            )
            raise UpstreamError("Qloo refused the request.")
        if status >= 300:
            logger.error("Qloo %s: unexpected HTTP %d", path, status)
            raise UpstreamError("Qloo returned an unexpected response.")
        try:
            body = response.json()
        except ValueError:
            logger.warning("Qloo %s: response was not JSON", path)
            return {}
        return body if isinstance(body, Mapping) else {}


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After", "")
    if retry_after.isdigit():
        return min(float(retry_after), MAX_RETRY_AFTER_SECONDS)
    return BACKOFF_SECONDS * 2 ** (attempt - 1)
