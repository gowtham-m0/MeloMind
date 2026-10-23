"""`MediaResolver` over the YouTube Data API v3: `search`, then `videos.list` to check each video.

A video is used only when `status.embeddable` is true, it's public, and its length suits one
item (no hour-long compilations). Never an unrelated video: when nothing fits, the answer is None.
"""

import asyncio
import html
import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from app.application.ports import PlayableMedia
from app.core.errors import UpstreamError

logger = logging.getLogger(__name__)

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"
YOUTUBE_TIMEOUT_SECONDS = 8.0
SEARCH_RESULTS = 5
MIN_DURATION_S = 60
MAX_DURATION_S = 600
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0

Sleep = Callable[[float], Awaitable[None]]

_ISO_DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


def parse_duration(text: str) -> int | None:
    """Seconds in an ISO 8601 duration such as `PT3M12S`, or None when it isn't one."""
    match = _ISO_DURATION.match(text)
    if match is None or not any(match.groups()):
        return None
    days, hours, minutes, seconds = (int(part) if part else 0 for part in match.groups())
    return ((days * 24 + hours) * 60 + minutes) * 60 + seconds


def _video_ids(body: Mapping[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in body.get("items", []):
        video_id = item.get("id", {}).get("videoId") if isinstance(item, Mapping) else None
        if isinstance(video_id, str):
            ids.append(video_id)
    return ids


def _playable(video: Mapping[str, Any]) -> PlayableMedia | None:
    status = video.get("status", {})
    if status.get("embeddable") is not True or status.get("privacyStatus") != "public":
        return None
    duration = parse_duration(str(video.get("contentDetails", {}).get("duration", "")))
    if duration is None or not MIN_DURATION_S <= duration <= MAX_DURATION_S:
        return None
    title = html.unescape(str(video.get("snippet", {}).get("title", "")))
    return PlayableMedia(video_id=str(video["id"]), title=title, duration_s=duration)


class YouTubeMediaResolver:
    """Finds an embeddable video of a suitable length. Each `search` costs 100 quota units.

    The key goes in the `X-Goog-Api-Key` header, never in the URL, so it can't reach a log.
    """

    def __init__(
        self, client: httpx.AsyncClient, api_key: str, *, sleep: Sleep = asyncio.sleep
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._sleep = sleep

    async def resolve(self, query: str) -> PlayableMedia | None:
        """The first search result that is embeddable, public and 1–10 minutes long."""
        found = await self._get(
            "/search",
            {
                "part": "snippet",
                "q": query,
                "type": "video",
                "videoEmbeddable": "true",
                "safeSearch": "strict",
                "maxResults": str(SEARCH_RESULTS),
            },
        )
        ids = _video_ids(found)
        if not ids:
            return None
        details = await self._get(
            "/videos", {"part": "status,contentDetails,snippet", "id": ",".join(ids)}
        )
        videos = {
            video["id"]: video
            for video in details.get("items", [])
            if isinstance(video, Mapping) and isinstance(video.get("id"), str)
        }
        for video_id in ids:
            video = videos.get(video_id)
            media = _playable(video) if video else None
            if media is not None:
                return media
        return None

    async def _get(self, path: str, params: dict[str, str]) -> Mapping[str, Any]:
        headers = {"X-Goog-Api-Key": self._api_key}
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = await self._client.get(path, params=params, headers=headers)
            except httpx.HTTPError as exc:
                logger.warning("YouTube %s failed: %s", path, type(exc).__name__)
                raise UpstreamError("YouTube didn't respond.") from exc
            # 429 means too many requests at once: wait a moment and try again.
            if response.status_code == 429 and attempt < MAX_ATTEMPTS:
                await self._sleep(BACKOFF_SECONDS * attempt)
                continue
            break
        if response.status_code >= 400:
            # 403 is usually the daily quota running out.
            logger.warning("YouTube %s: HTTP %d", path, response.status_code)
            raise UpstreamError("YouTube refused the request.")
        try:
            body = response.json()
        except ValueError as exc:
            raise UpstreamError("YouTube returned an unexpected response.") from exc
        return body if isinstance(body, Mapping) else {}
