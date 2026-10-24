"""The "New and notable" row asks for films and TV from the last couple of years."""

from datetime import date
from uuid import uuid4

from app.application.agent.types import FeedContext, SignalRef
from app.application.rows.rows import NewReleasesRow
from app.domain.feedback import Blocklist
from app.domain.models import EntityType


def context(signals: tuple[SignalRef, ...]) -> FeedContext:
    return FeedContext(
        profile_id=uuid4(),
        first_name="Aanya",
        birth_year=None,
        country_code="IN",
        favourite_signals=signals,
        learned_signals=(),
        text_favourites=(),
        song_titles=(),
        blocklist=Blocklist.from_exclusions([]),
    )


def test_new_releases_ask_for_recent_films_and_tv_steered_by_taste() -> None:
    signal = SignalRef(ref="s1", name="Glass Animals", entity_type=EntityType.ARTIST)

    [spec] = NewReleasesRow().specs(context((signal,)), [])

    assert {query.entity_type for query in spec.queries} == {EntityType.MOVIE, EntityType.TV_SHOW}
    assert all(query.year_min == date.today().year - 1 for query in spec.queries)
    assert all(query.signal_ids == ("s1",) for query in spec.queries)


def test_new_releases_without_taste_fall_back_to_popular_in_the_country() -> None:
    [spec] = NewReleasesRow().specs(context(()), [])

    assert all(query.popularity_min and query.country_code == "IN" for query in spec.queries)
