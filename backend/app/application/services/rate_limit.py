"""A per-user rate limit for feed builds, which cost Qloo and LLM calls."""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from uuid import UUID

from app.core.errors import RateLimitedError

WINDOW_SECONDS = 3600.0


class SlidingWindowRateLimiter:
    """At most `limit` requests per user in any `window` seconds. Kept in memory per process."""

    def __init__(
        self,
        limit: int,
        window: float = WINDOW_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window
        self._clock = clock
        self._hits: defaultdict[UUID, deque[float]] = defaultdict(deque)

    def check(self, user_id: UUID) -> None:
        """Count one request, or raise `RateLimitedError` when the user is over the limit."""
        now = self._clock()
        hits = self._hits[user_id]
        while hits and now - hits[0] >= self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            minutes = max(round((self._window - (now - hits[0])) / 60), 1)
            raise RateLimitedError(
                f"That's {self._limit} refreshes this hour. "
                f"Please try again in about {minutes} min."
            )
        hits.append(now)
