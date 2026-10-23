"""Use cases over the taste graph: finding entities by name for favourites and the demo seed."""

from app.application.ports import EntityMatch, TasteGraph, TasteSource
from app.core.errors import InvalidInputError
from app.domain.models import EntityType, FavouriteKind, search_type_for
from app.domain.names import names_match

SEARCH_TAKE = 8
QUERY_MAX_LENGTH = 100


class TasteService:
    """Searches Qloo (or the demo fixtures). Songs are searched by singer, never by title."""

    def __init__(self, taste_graph: TasteGraph) -> None:
        self._taste_graph = taste_graph

    @property
    def source(self) -> TasteSource:
        """Where results come from: live Qloo or the demo fixtures."""
        return self._taste_graph.source

    async def search(self, query: str, kind: FavouriteKind | None = None) -> list[EntityMatch]:
        """Matches for a name the caregiver typed, of the type the favourite's kind needs."""
        text = " ".join(query.split())
        if not text:
            raise InvalidInputError("Type a name to search for.")
        if len(text) > QUERY_MAX_LENGTH:
            raise InvalidInputError(f"Keep the search under {QUERY_MAX_LENGTH} characters.")
        types: tuple[EntityType, ...] = (search_type_for(kind),) if kind else ()
        return await self._taste_graph.search(text, types, SEARCH_TAKE)

    async def find_by_name(self, name: str, kind: FavouriteKind) -> EntityMatch | None:
        """The match whose name is the same as `name` and whose type fits the kind, if any."""
        matches = await self.search(name, kind)
        return next((match for match in matches if names_match(match.name, name)), None)
