"""Qloo's entity type URNs and how they map to our entity types."""

from app.domain.models import EntityType

URN_BY_TYPE: dict[EntityType, str] = {
    EntityType.ARTIST: "urn:entity:artist",
    EntityType.MOVIE: "urn:entity:movie",
    EntityType.TV_SHOW: "urn:entity:tv_show",
    EntityType.BOOK: "urn:entity:book",
}

TYPE_BY_URN: dict[str, EntityType] = {urn: entity_type for entity_type, urn in URN_BY_TYPE.items()}

# Qloo filters by release year for films and TV, and by publication year for books. Artists have
# no year filter at all (docs/QLOO_NOTES.md, section 3).
RELEASE_YEAR_TYPES = frozenset({EntityType.MOVIE, EntityType.TV_SHOW})
PUBLICATION_YEAR_TYPES = frozenset({EntityType.BOOK})
YEAR_FILTER_TYPES = RELEASE_YEAR_TYPES | PUBLICATION_YEAR_TYPES
# `filter.release_country` works for films and TV only.
COUNTRY_FILTER_TYPES = frozenset({EntityType.MOVIE, EntityType.TV_SHOW})
