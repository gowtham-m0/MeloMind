"""What to search for when finding a video for an item (docs/AGENT.md, section 3)."""

from app.domain.models import EntityType


def decade_of(year: int) -> int:
    """The decade a year falls in: 1964 → 1960."""
    return year // 10 * 10


def media_query(
    title: str,
    entity_type: EntityType,
    release_year: int | None,
    era_year: int,
    song_title: str | None = None,
) -> str | None:
    """The video search for an item, or None for a book, which has no video.

    A song searches its title and singer. An artist searches its name and decade, and films and
    TV their year, so the video is from the right time. `era_year` stands in when the year is
    unknown, as it is for artists from live Qloo.
    """
    if song_title:
        return f"{song_title} {title}"
    when = str(release_year) if release_year else f"{decade_of(era_year)}s"
    match entity_type:
        case EntityType.ARTIST:
            return f"{title} {decade_of(release_year or era_year)}s hit song"
        case EntityType.MOVIE:
            return f"{title} {when} film clip"
        case EntityType.TV_SHOW:
            return f"{title} {when} TV theme"
        case EntityType.BOOK:
            return None
