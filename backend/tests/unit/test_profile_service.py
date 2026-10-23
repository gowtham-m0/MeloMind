"""Tests for ProfileService: ownership, validation, favourites and cascading deletes."""

from uuid import UUID, uuid4

import pytest

from app.application.services.profiles import ProfileChanges, ProfileService
from app.core.errors import InvalidInputError, NotFoundError
from app.domain.models import FavouriteKind
from app.infrastructure.persistence.memory_profiles import InMemoryProfileRepository

pytestmark = pytest.mark.anyio

OWNER = uuid4()
STRANGER = uuid4()


@pytest.fixture
def service() -> ProfileService:
    return ProfileService(InMemoryProfileRepository())


async def create(service: ProfileService, **changes: object) -> UUID:
    profile = await service.create(OWNER, "Margaret", 1948, ProfileChanges(**changes))  # type: ignore[typeddict-item]
    return profile.id


async def test_create_with_only_name_and_birth_year(service: ProfileService) -> None:
    profile = await service.create(OWNER, "  Margaret  ", 1948, ProfileChanges())

    assert profile.display_name == "Margaret"
    assert profile.country_code is None
    assert profile.places_lived == []
    assert [p.id for p in await service.list(OWNER)] == [profile.id]


@pytest.mark.parametrize("birth_year", [1919, 1991])
async def test_create_rejects_birth_year_out_of_range(
    service: ProfileService, birth_year: int
) -> None:
    with pytest.raises(InvalidInputError):
        await service.create(OWNER, "Margaret", birth_year, ProfileChanges())


async def test_other_users_profiles_are_not_found(service: ProfileService) -> None:
    profile_id = await create(service)

    with pytest.raises(NotFoundError):
        await service.get(STRANGER, profile_id)
    with pytest.raises(NotFoundError):
        await service.update(STRANGER, profile_id, ProfileChanges(display_name="Mallory"))
    with pytest.raises(NotFoundError):
        await service.delete(STRANGER, profile_id)
    with pytest.raises(NotFoundError):
        await service.add_favourite(STRANGER, profile_id, "The Supremes", FavouriteKind.ARTIST)
    assert await service.list(STRANGER) == []
    assert (await service.get(OWNER, profile_id)).display_name == "Margaret"


async def test_update_changes_only_the_given_fields(service: ProfileService) -> None:
    profile_id = await create(service, places_lived=["Chicago"])

    updated = await service.update(
        OWNER, profile_id, ProfileChanges(country_code="us", languages=[" English ", ""])
    )

    assert updated.country_code == "US"
    assert updated.languages == ["English"]
    assert updated.places_lived == ["Chicago"]
    assert updated.display_name == "Margaret"


async def test_verified_and_text_favourites(service: ProfileService) -> None:
    profile_id = await create(service)

    verified = await service.add_favourite(
        OWNER,
        profile_id,
        "The Supremes",
        FavouriteKind.ARTIST,
        entity_id="demo-artist-the-supremes",
    )
    text = await service.add_favourite(
        OWNER, profile_id, "Our wedding song", FavouriteKind.SONG, song_title="Moon River"
    )

    assert verified.verified and verified.qloo_id == "demo-artist-the-supremes"
    assert not text.verified and text.song_title == "Moon River"
    favourites = (await service.get(OWNER, profile_id)).favourites
    assert [favourite.id for favourite in favourites] == [verified.id, text.id]


async def test_adding_the_same_favourite_twice_keeps_one(service: ProfileService) -> None:
    profile_id = await create(service)

    first = await service.add_favourite(
        OWNER,
        profile_id,
        "The Supremes",
        FavouriteKind.ARTIST,
        entity_id="demo-artist-the-supremes",
    )
    second = await service.add_favourite(
        OWNER,
        profile_id,
        "The Supremes",
        FavouriteKind.ARTIST,
        entity_id="demo-artist-the-supremes",
    )

    assert first.id == second.id
    assert len((await service.get(OWNER, profile_id)).favourites) == 1


async def test_song_title_only_for_songs(service: ProfileService) -> None:
    profile_id = await create(service)

    with pytest.raises(InvalidInputError):
        await service.add_favourite(
            OWNER, profile_id, "The Supremes", FavouriteKind.ARTIST, song_title="Baby Love"
        )


async def test_remove_favourite(service: ProfileService) -> None:
    profile_id = await create(service)
    favourite = await service.add_favourite(OWNER, profile_id, "Abba", FavouriteKind.ARTIST)

    await service.remove_favourite(OWNER, profile_id, favourite.id)

    assert (await service.get(OWNER, profile_id)).favourites == []
    with pytest.raises(NotFoundError):
        await service.remove_favourite(OWNER, profile_id, favourite.id)


async def test_delete_removes_the_profile_and_its_favourites() -> None:
    repository = InMemoryProfileRepository()
    service = ProfileService(repository)
    profile_id = await create(service)
    await service.add_favourite(OWNER, profile_id, "Abba", FavouriteKind.ARTIST)

    await service.delete(OWNER, profile_id)

    assert await repository.get(profile_id) is None
    with pytest.raises(NotFoundError):
        await service.get(OWNER, profile_id)
