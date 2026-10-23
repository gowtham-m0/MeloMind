"""`MediaResolver` for demo mode, used when `YOUTUBE_API_KEY` is empty.

Every query gets demo media with a steady, song-like length, so sessions can be planned, timed
and "played" without YouTube. The UI shows it as demo media, never as a real video.
"""

import hashlib

from app.application.ports import PlayableMedia

DEMO_MIN_SECONDS = 150
DEMO_SPREAD_SECONDS = 90


class DemoMediaResolver:
    """Gives each query the same demo media every time."""

    async def resolve(self, query: str) -> PlayableMedia | None:
        """Demo media for the query, 2.5 to 4 minutes long."""
        digest = hashlib.sha256(query.casefold().encode("utf-8")).hexdigest()
        return PlayableMedia(
            video_id=f"demo-{digest[:11]}",
            title=query,
            duration_s=DEMO_MIN_SECONDS + int(digest[:4], 16) % DEMO_SPREAD_SECONDS,
            provider="demo",
        )
