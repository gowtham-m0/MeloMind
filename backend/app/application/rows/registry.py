"""The `RowRegistry`: the feed's rows, in order. Earlier rows take items first."""

from collections.abc import Iterable

from app.application.rows.base import FeedRow
from app.application.rows.rows import (
    BecauseRow,
    CrossCultureRow,
    ForYouRow,
    NewReleasesRow,
    PopularRow,
    ThrowbackRow,
    TypeRow,
)
from app.domain.models import EntityType


class RowRegistry:
    """The rows in display order."""

    def __init__(self, rows: Iterable[FeedRow]) -> None:
        self._rows = list(rows)

    @property
    def rows(self) -> list[FeedRow]:
        """Every registered row, in order."""
        return list(self._rows)


def default_registry(row_size: int = 12) -> RowRegistry:
    """The rows available now. The journal row arrives in Phase 3."""
    return RowRegistry(
        [
            ForYouRow(row_size=row_size),
            CrossCultureRow(),
            BecauseRow(),
            TypeRow(
                "music",
                EntityType.ARTIST,
                "Music for you",
                "Artists you'll probably love",
                row_size,
            ),
            TypeRow("films", EntityType.MOVIE, "Films for you", "Picked from your taste", row_size),
            TypeRow(
                "tv", EntityType.TV_SHOW, "TV shows for you", "Series worth starting", row_size
            ),
            TypeRow("books", EntityType.BOOK, "Books for you", "Your next great read", row_size),
            NewReleasesRow(),
            PopularRow(),
            ThrowbackRow(),
        ]
    )
