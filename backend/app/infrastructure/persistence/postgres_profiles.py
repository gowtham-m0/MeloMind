"""`ProfileRepository` on Postgres with SQLAlchemy."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import Favourite, FavouriteKind, Profile
from app.infrastructure.persistence.models import FavouriteRow, ProfileRow


def _favourite_to_domain(row: FavouriteRow) -> Favourite:
    return Favourite(
        id=row.id,
        profile_id=row.profile_id,
        name=row.name,
        kind=FavouriteKind(row.kind),
        qloo_id=row.qloo_id,
        song_title=row.song_title,
        created_at=row.created_at,
    )


def _favourite_to_row(favourite: Favourite) -> FavouriteRow:
    return FavouriteRow(
        id=favourite.id,
        profile_id=favourite.profile_id,
        name=favourite.name,
        kind=favourite.kind.value,
        qloo_id=favourite.qloo_id,
        song_title=favourite.song_title,
        created_at=favourite.created_at,
    )


def _profile_to_domain(row: ProfileRow) -> Profile:
    return Profile(
        id=row.id,
        owner_id=row.owner_id,
        display_name=row.display_name,
        birth_year=row.birth_year,
        country_code=row.country_code,
        places_lived=list(row.places_lived),
        languages=list(row.languages),
        is_demo=row.is_demo,
        favourites=[_favourite_to_domain(favourite) for favourite in row.favourites],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PostgresProfileRepository:
    """Profiles and favourites in Postgres. The database cascades profile deletes."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def list_for_owner(self, owner_id: UUID) -> list[Profile]:
        """Every profile the user owns, oldest first."""
        async with self._sessions() as session:
            rows = await session.scalars(
                select(ProfileRow)
                .where(ProfileRow.owner_id == owner_id)
                .order_by(ProfileRow.created_at)
            )
            return [_profile_to_domain(row) for row in rows]

    async def get(self, profile_id: UUID) -> Profile | None:
        """One profile with its favourites."""
        async with self._sessions() as session:
            row = await session.get(ProfileRow, profile_id)
            return _profile_to_domain(row) if row else None

    async def add(self, profile: Profile) -> None:
        """Store a new profile and its favourites."""
        async with self._sessions() as session, session.begin():
            session.add(
                ProfileRow(
                    id=profile.id,
                    owner_id=profile.owner_id,
                    display_name=profile.display_name,
                    birth_year=profile.birth_year,
                    country_code=profile.country_code,
                    places_lived=profile.places_lived,
                    languages=profile.languages,
                    is_demo=profile.is_demo,
                    created_at=profile.created_at,
                    updated_at=profile.updated_at,
                    favourites=[_favourite_to_row(favourite) for favourite in profile.favourites],
                )
            )

    async def update(self, profile: Profile) -> None:
        """Save the profile's own fields."""
        async with self._sessions() as session, session.begin():
            row = await session.get(ProfileRow, profile.id)
            if row is None:
                return
            row.display_name = profile.display_name
            row.birth_year = profile.birth_year
            row.country_code = profile.country_code
            row.places_lived = profile.places_lived
            row.languages = profile.languages
            row.updated_at = profile.updated_at

    async def delete(self, profile_id: UUID) -> None:
        """Delete the profile; `ON DELETE CASCADE` removes its favourites."""
        async with self._sessions() as session, session.begin():
            await session.execute(delete(ProfileRow).where(ProfileRow.id == profile_id))

    async def add_favourite(self, favourite: Favourite) -> None:
        """Store a new favourite on its profile."""
        async with self._sessions() as session, session.begin():
            session.add(_favourite_to_row(favourite))

    async def delete_favourite(self, profile_id: UUID, favourite_id: UUID) -> bool:
        """Delete one favourite of this profile. False when there was none."""
        async with self._sessions() as session, session.begin():
            result = await session.execute(
                delete(FavouriteRow).where(
                    FavouriteRow.id == favourite_id, FavouriteRow.profile_id == profile_id
                )
            )
            return result.rowcount > 0
