"""Taste search route: names to Qloo entities, for the favourites editor."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, TasteServiceDep
from app.api.v1.schemas.taste import EntityMatchOut
from app.domain.models import FavouriteKind

router = APIRouter(prefix="/taste", tags=["taste"])


@router.get("/search")
async def search_taste(
    q: Annotated[str, Query(min_length=1, max_length=100)],
    _user: CurrentUserDep,
    taste: TasteServiceDep,
    kind: Annotated[FavouriteKind | None, Query(alias="type")] = None,
) -> list[EntityMatchOut]:
    """Matches for a name. For a song, search the singer: Qloo has no songs."""
    return [EntityMatchOut.from_match(match) for match in await taste.search(q, kind)]
