"""Tests for the session state machine, the blocklist, refs and media queries."""

from uuid import uuid4

import pytest

from app.domain.feedback import Blocklist, Exclusion, ExclusionKind
from app.domain.media import media_query
from app.domain.models import EntityType, Favourite, FavouriteKind
from app.domain.sessions import Session, SessionStatus, favourite_ref

S = SessionStatus


def session(status: SessionStatus, mode: str = "standard") -> Session:
    return Session(profile_id=uuid4(), mode=mode, target_minutes=20, status=status)


@pytest.mark.parametrize(
    ("start", "to"),
    [
        (S.PLANNING, S.DRAFT),
        (S.PLANNING, S.FAILED),
        (S.DRAFT, S.APPROVED),
        (S.APPROVED, S.IN_PROGRESS),
        (S.IN_PROGRESS, S.COMPLETED),
    ],
)
def test_allowed_status_changes(start: SessionStatus, to: SessionStatus) -> None:
    assert session(start).can_move_to(to)


@pytest.mark.parametrize(
    ("start", "to"),
    [
        (S.PLANNING, S.APPROVED),
        (S.DRAFT, S.IN_PROGRESS),
        (S.DRAFT, S.DRAFT),
        (S.APPROVED, S.APPROVED),
        (S.APPROVED, S.COMPLETED),
        (S.COMPLETED, S.IN_PROGRESS),
        (S.FAILED, S.DRAFT),
    ],
)
def test_forbidden_status_changes(start: SessionStatus, to: SessionStatus) -> None:
    assert not session(start).can_move_to(to)


def test_a_warmup_set_stops_at_approved() -> None:
    assert session(S.DRAFT, "warmup").can_move_to(S.APPROVED)
    assert not session(S.APPROVED, "warmup").can_move_to(S.IN_PROGRESS)


def test_favourite_refs_use_the_qloo_id_except_for_songs() -> None:
    profile = uuid4()
    artist = Favourite(profile, "The Supremes", FavouriteKind.ARTIST, qloo_id="q1")
    song = Favourite(profile, "The Temptations", FavouriteKind.SONG, "q2", song_title="My Girl")
    typed = Favourite(profile, "Some Film", FavouriteKind.MOVIE)

    assert favourite_ref(artist) == "q1"
    assert favourite_ref(song) == f"fav:{song.id}"
    assert favourite_ref(typed) == f"fav:{typed.id}"


def test_the_blocklist_matches_ids_and_typed_favourites_by_name() -> None:
    profile = uuid4()
    blocklist = Blocklist.from_exclusions(
        [
            Exclusion(profile, "q1", "The Four Tops", ExclusionKind.REJECTED),
            Exclusion(profile, "fav:x", "Moon River", ExclusionKind.HIDDEN),
        ]
    )

    assert blocklist.blocks("q1", "anything")
    assert blocklist.blocks("fav:other", "moon  river!")
    assert not blocklist.blocks("q2", "Moon River")
    assert blocklist.qloo_ids == ("q1",)


def test_media_queries_follow_the_type() -> None:
    assert media_query("The Supremes", EntityType.ARTIST, None, 1965) == (
        "The Supremes 1960s hit song"
    )
    assert media_query("Bewitched", EntityType.TV_SHOW, 1964, 1965) == "Bewitched 1964 TV theme"
    assert media_query("Mary Poppins", EntityType.MOVIE, 1964, 1965) == (
        "Mary Poppins 1964 film clip"
    )
    assert media_query("A Book", EntityType.BOOK, 1962, 1965) is None
    assert media_query("The Temptations", EntityType.ARTIST, None, 1965, "My Girl") == (
        "My Girl The Temptations"
    )
