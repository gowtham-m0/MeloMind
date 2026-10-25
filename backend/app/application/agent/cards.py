"""Turning candidates into feed cards: the reason, the image and the platform links.

Shared by the `decorate` node and the services that show items outside the feed ("More like
this", the taste quiz).
"""

from collections import Counter
from collections.abc import Sequence

from app.application.agent.types import Candidate
from app.application.ports import EntityMatch, Song
from app.domain.feed import FeedItem, ItemSource, song_ref
from app.domain.links import platform_links
from app.domain.models import EntityType
from app.domain.names import normalise_name

OPEN_LIBRARY_COVER = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
REASON_MAX = 120
TASTE_TAGS_MAX = 8
TAG_SYNONYMS = {
    "sci fi": "science fiction",
    "scifi": "science fiction",
    "rom com": "romantic comedy",
}
GENERIC_TAGS = frozenset(
    {
        "fiction",
        "contemporary",
        "non fiction",
        "nonfiction",
        "fiction books",
        "audiobook",
        "adult",
        "adult fiction",
    }
)


def reason_for(candidate: Candidate, fixed: str | None = None) -> str:
    """One line on why the card is here (rule 2). A row's fixed reason wins."""
    if fixed:
        return fixed
    basis = " ".join(candidate.signal.split())
    if not basis:
        return "Picked for you by Qloo."
    text = basis[0].upper() + basis[1:]
    text = text if text.endswith(".") else f"{text}."
    return text if len(text) <= REASON_MAX else f"{text[: REASON_MAX - 1]}…"


def image_for(candidate: Candidate) -> str | None:
    """Qloo's image, else an Open Library cover for a book with an ISBN (URLs only, rule 13)."""
    if candidate.image_url:
        return candidate.image_url
    if candidate.entity_type is EntityType.BOOK and candidate.isbn13:
        return OPEN_LIBRARY_COVER.format(isbn=candidate.isbn13)
    return None


def candidate_from_match(
    match: EntityMatch,
    signal: str,
    because_ref: str | None = None,
    because_name: str | None = None,
) -> Candidate:
    """A candidate for a taste-graph result found outside the agent ("More like this", the quiz)."""
    return Candidate(
        entity_id=match.entity_id,
        name=match.name,
        entity_type=match.type,
        source=ItemSource(match.source),
        signal=signal,
        because_ref=because_ref,
        because_name=because_name,
        release_year=match.release_year,
        popularity=match.popularity,
        affinity=match.affinity,
        image_url=match.image_url,
        description=match.description,
        isbn13=match.isbn13,
        tags=match.tags,
        external=tuple(sorted(match.external.items())),
    )


def candidate_from_song(
    song: Song,
    artist_ref: str,
    artist_name: str,
    signal: str,
    because_ref: str | None = None,
    because_name: str | None = None,
) -> Candidate:
    """A song card's candidate. The pick is Qloo's (the artist); the song is a catalogue lookup,
    so `parent_ref` keeps the artist, and excluding the artist removes the song."""
    return Candidate(
        entity_id=song_ref(song.track_id),
        name=song.title,
        entity_type=EntityType.SONG,
        source=ItemSource.SONG_CATALOGUE,
        signal=signal,
        because_ref=because_ref,
        because_name=because_name,
        release_year=song.year,
        image_url=song.artwork_url,
        description=song.album,
        creator=song.artist_credit,
        parent_ref=artist_ref,
        parent_name=artist_name,
        preview_url=song.preview_url,
        store_url=song.store_url,
    )


def to_card(candidate: Candidate, country_code: str | None, reason: str | None = None) -> FeedItem:
    """A feed card for the candidate."""
    return FeedItem(
        ref=candidate.entity_id,
        title=candidate.name,
        entity_type=candidate.entity_type,
        source=candidate.source,
        reason=reason_for(candidate, reason),
        because_of_ref=candidate.because_ref,
        because_of_title=candidate.because_name,
        year=candidate.release_year,
        image_url=image_for(candidate),
        affinity=candidate.affinity,
        popularity=candidate.popularity,
        tags=candidate.tags[:4],
        description=candidate.description,
        links=platform_links(
            candidate.name,
            candidate.entity_type,
            country_code=country_code,
            year=candidate.release_year,
            external=dict(candidate.external),
            isbn13=candidate.isbn13,
            creator=candidate.creator,
            store_url=candidate.store_url,
        ),
        creator=candidate.creator,
        parent_ref=candidate.parent_ref,
        parent_title=candidate.parent_name,
        preview_url=candidate.preview_url,
    )


def tag_key(tag: str) -> str:
    """A tag's comparison key: normalised, with synonyms merged ("Sci fi" is "science fiction")."""
    key = normalise_name(tag)
    return TAG_SYNONYMS.get(key, key)


def taste_tags(candidates: Sequence[Candidate]) -> tuple[str, ...]:
    """The tags that come up most among strong matches, for the sidebar's taste chips. Synonyms
    ("Sci fi", "Science fiction") count as one, and catch-all tags ("Fiction") are left out."""
    weights: Counter[str] = Counter()
    shown: dict[str, str] = {}
    for candidate in candidates:
        weight = candidate.affinity if candidate.affinity is not None else 0.5
        for tag in candidate.tags:
            key = tag_key(tag)
            if key in GENERIC_TAGS:
                continue
            shown.setdefault(key, tag)
            weights[key] += weight
    return tuple(shown[key] for key, _ in weights.most_common(TASTE_TAGS_MAX))
