"""Tests for the demo seed: idempotent, favourites resolved by name, and the sample likes and
exclusion."""

from uuid import uuid4

import pytest

from app.application.ports import EntityMatch, InsightsQuery, TasteGraph, TasteSource
from app.application.services.demo import DemoSeedService
from app.application.services.taste import TasteService
from app.core.errors import UpstreamError
from app.domain.feedback import Signal
from app.domain.models import EntityType
from app.infrastructure.persistence.memory_feedback import (
    InMemoryExclusionRepository,
    InMemoryFeedbackRepository,
)
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


class Seeded:
    """A demo seed over in-memory repositories, with the repositories to check afterwards."""

    def __init__(self, graph: TasteGraph | None = None) -> None:
        self.profiles = InMemoryProfileRepository()
        self.feedback = InMemoryFeedbackRepository()
        self.exclusions = InMemoryExclusionRepository()
        self.seed = DemoSeedService(
            self.profiles,
            TasteService(graph or FixtureTasteGraph()),
            load_demo_profiles(),
            self.feedback,
            self.exclusions,
        )


async def test_seed_creates_the_sample_profiles_with_verified_favourites() -> None:
    seeded = Seeded()
    repository, seed = seeded.profiles, seeded.seed
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
    seeded = Seeded()
    repository, seed = seeded.profiles, seeded.seed
    owner, other = uuid4(), uuid4()

    first = await seed.seed(owner)
    second = await seed.seed(owner)
    others = await seed.seed(other)

    assert first == second
    assert len(await repository.list_for_owner(owner)) == 2
    assert set(others).isdisjoint(first)


async def test_seed_keeps_favourites_as_text_when_search_fails() -> None:
    seeded = Seeded(FailingTasteGraph())
    repository, seed = seeded.profiles, seeded.seed
    owner = uuid4()

    await seed.seed(owner)

    profiles = await repository.list_for_owner(owner)
    favourites = [favourite for profile in profiles for favourite in profile.favourites]
    assert len(favourites) == 9
    assert not any(favourite.verified for favourite in favourites)


async def test_seed_adds_the_sample_likes_and_one_exclusion() -> None:
    seeded = Seeded()
    owner = uuid4()

    aanya_id, leo_id = await seeded.seed.seed(owner)

    aanya = await seeded.feedback.list_for_profile(aanya_id)
    assert {(entry.title, entry.kind) for entry in aanya} == {
        ("Tame Impala", Signal.LIKED),
        ("Dune", Signal.LIKED),
        ("Euphoria", Signal.NOT_INTERESTED),
    }
    excluded = await seeded.exclusions.list_for_profile(aanya_id)
    assert [(entry.title, entry.entity_type) for entry in excluded] == [
        ("Euphoria", EntityType.TV_SHOW)
    ]
    assert all(not entry.entity_ref.startswith("fav:") for entry in excluded)
    leo = await seeded.feedback.list_for_profile(leo_id)
    assert len(leo) == 3
    assert await seeded.exclusions.list_for_profile(leo_id) == []


async def test_seed_skips_likes_search_cannot_find() -> None:
    seeded = Seeded(FailingTasteGraph())
    owner = uuid4()

    ids = await seeded.seed.seed(owner)

    for profile_id in ids:
        assert await seeded.feedback.list_for_profile(profile_id) == []
        assert await seeded.exclusions.list_for_profile(profile_id) == []
