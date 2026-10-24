"""Tests for the demo seed: idempotent, and favourites resolved by name."""

from uuid import uuid4

import pytest

from app.application.ports import EntityMatch, InsightsQuery, TasteSource
from app.application.services.demo import DemoSeedService
from app.application.services.taste import TasteService
from app.core.errors import UpstreamError
from app.domain.models import EntityType
from app.infrastructure.persistence.memory_profiles import InMemoryProfileRepository
from app.infrastructure.qloo.demo_profiles import load_demo_profiles
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph

pytestmark = pytest.mark.anyio


class FailingTasteGraph:
    """A taste graph whose every call fails, like Qloo timing out."""

    @property
    def source(self) -> TasteSource:
        return "qloo_live"

    async def search(
        self, query: str, types: tuple[EntityType, ...] = (), take: int = 5
    ) -> list[EntityMatch]:
        raise UpstreamError("Qloo didn't respond.")

    async def insights(self, query: InsightsQuery) -> list[EntityMatch]:
        raise UpstreamError("Qloo didn't respond.")


async def test_seed_creates_the_sample_profiles_with_verified_favourites() -> None:
    repository = InMemoryProfileRepository()
    seed = DemoSeedService(repository, TasteService(FixtureTasteGraph()), load_demo_profiles())
    owner = uuid4()

    ids = await seed.seed(owner)

    profiles = await repository.list_for_owner(owner)
    assert [profile.id for profile in profiles] == ids
    assert [profile.display_name for profile in profiles] == ["Aanya", "Leo"]
    assert all(profile.is_demo for profile in profiles)
    favourites = [favourite for profile in profiles for favourite in profile.favourites]
    assert len(favourites) == 9
    assert all(favourite.verified for favourite in favourites)
    my_girl = next(favourite for favourite in favourites if favourite.song_title == "My Girl")
    assert my_girl.name == "The Temptations"
    assert my_girl.qloo_id == "demo-artist-the-temptations"


async def test_seed_is_idempotent_per_user() -> None:
    repository = InMemoryProfileRepository()
    seed = DemoSeedService(repository, TasteService(FixtureTasteGraph()), load_demo_profiles())
    owner, other = uuid4(), uuid4()

    first = await seed.seed(owner)
    second = await seed.seed(owner)
    others = await seed.seed(other)

    assert first == second
    assert len(await repository.list_for_owner(owner)) == 2
    assert set(others).isdisjoint(first)


async def test_seed_keeps_favourites_as_text_when_search_fails() -> None:
    repository = InMemoryProfileRepository()
    seed = DemoSeedService(repository, TasteService(FailingTasteGraph()), load_demo_profiles())
    owner = uuid4()

    await seed.seed(owner)

    profiles = await repository.list_for_owner(owner)
    favourites = [favourite for profile in profiles for favourite in profile.favourites]
    assert len(favourites) == 9
    assert not any(favourite.verified for favourite in favourites)
