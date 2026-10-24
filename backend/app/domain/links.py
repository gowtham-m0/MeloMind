"""Where to find an item: platform links built from its title, type, country and Qloo's external
IDs. No streaming-availability API: a search link says "Search on …", and only a link built from a
trusted external ID says "Open on …" or "Listen on …" (rule 5)."""

import re
from collections.abc import Mapping
from urllib.parse import quote, quote_plus

from app.domain.feed import PlatformLink
from app.domain.models import EntityType

_SPOTIFY_ID = re.compile(r"^[A-Za-z0-9]{22}$")
_DIGITS = re.compile(r"^\d{1,12}$")
_IMDB_TITLE = re.compile(r"^tt\d{5,10}$")
_GOODREADS_ID = re.compile(r"^\d{1,12}(?:[.-][\w-]{0,80})?$")
_ISBN13 = re.compile(r"^\d{13}$")
_APPLE_MUSIC_URL = re.compile(r"^https://music\.apple\.com/[\w/.%?=&-]{1,300}$")

# JustWatch uses its own path for a few countries; the rest use the lower-case ISO code.
_JUSTWATCH_PATHS = {"GB": "uk"}
_AMAZON_DOMAINS = {
    "IN": "amazon.in",
    "GB": "amazon.co.uk",
    "CA": "amazon.ca",
    "AU": "amazon.com.au",
    "DE": "amazon.de",
    "FR": "amazon.fr",
    "JP": "amazon.co.jp",
}
DEFAULT_COUNTRY = "US"


def _search(platform: str, name: str, url: str) -> PlatformLink:
    return PlatformLink(platform=platform, label=f"Search on {name}", url=url, kind="search")


def _direct(platform: str, label: str, url: str) -> PlatformLink:
    return PlatformLink(platform=platform, label=label, url=url, kind="direct")


def _country(country_code: str | None) -> str:
    code = (country_code or "").strip().upper()
    return code if len(code) == 2 and code.isalpha() else DEFAULT_COUNTRY


def _music_links(query: str, external: Mapping[str, str]) -> list[PlatformLink]:
    q = quote_plus(query)
    links = [_search("youtube", "YouTube", f"https://www.youtube.com/results?search_query={q}")]
    spotify_id = external.get("spotify", "")
    if _SPOTIFY_ID.match(spotify_id):
        links.insert(
            0,
            _direct(
                "spotify", "Listen on Spotify", f"https://open.spotify.com/artist/{spotify_id}"
            ),
        )
    else:
        links.append(
            _search("spotify", "Spotify", f"https://open.spotify.com/search/{quote(query)}")
        )
    links.append(
        _search("youtube_music", "YouTube Music", f"https://music.youtube.com/search?q={q}")
    )
    links.append(_search("apple_music", "Apple Music", f"https://music.apple.com/search?term={q}"))
    return links


def _song_links(title: str, creator: str | None, store_url: str | None) -> list[PlatformLink]:
    """Apple Music first: the catalogue that gave us the song, a direct link (rule 5)."""
    query = f"{title} {creator}" if creator else title
    q = quote_plus(query)
    links: list[PlatformLink] = []
    if store_url and _APPLE_MUSIC_URL.match(store_url):
        links.append(_direct("apple_music", "Listen on Apple Music", store_url))
    else:
        links.append(
            _search("apple_music", "Apple Music", f"https://music.apple.com/search?term={q}")
        )
    links.append(_search("youtube", "YouTube", f"https://www.youtube.com/results?search_query={q}"))
    links.append(_search("spotify", "Spotify", f"https://open.spotify.com/search/{quote(query)}"))
    links.append(
        _search("youtube_music", "YouTube Music", f"https://music.youtube.com/search?q={q}")
    )
    return links


def _screen_links(
    title: str, year: int | None, country: str, external: Mapping[str, str]
) -> list[PlatformLink]:
    q = quote_plus(title)
    path = _JUSTWATCH_PATHS.get(country, country.lower())
    links: list[PlatformLink] = []
    netflix_id = external.get("netflix", "")
    if _DIGITS.match(netflix_id):
        links.append(
            _direct("netflix", "Open on Netflix", f"https://www.netflix.com/title/{netflix_id}")
        )
    links.append(
        _search("justwatch", "JustWatch", f"https://www.justwatch.com/{path}/search?q={q}")
    )
    if links[0].platform != "netflix":
        links.append(_search("netflix", "Netflix", f"https://www.netflix.com/search?q={q}"))
    links.append(
        _search(
            "prime_video",
            "Prime Video",
            f"https://www.primevideo.com/search/ref=atv_nb_sug?phrase={q}",
        )
    )
    imdb_id = external.get("imdb", "")
    if _IMDB_TITLE.match(imdb_id):
        links.append(_direct("imdb", "Open on IMDb", f"https://www.imdb.com/title/{imdb_id}/"))
    trailer = quote_plus(f"{title} {year} trailer" if year else f"{title} trailer")
    links.append(
        _search("youtube", "YouTube", f"https://www.youtube.com/results?search_query={trailer}")
    )
    return links


def _book_links(
    title: str, country: str, external: Mapping[str, str], isbn13: str | None
) -> list[PlatformLink]:
    q = quote_plus(title)
    links: list[PlatformLink] = []
    if isbn13 and _ISBN13.match(isbn13):
        links.append(
            _direct(
                "google_books",
                "Open on Google Books",
                f"https://books.google.com/books?vid=ISBN{isbn13}",
            )
        )
    else:
        links.append(
            _search("google_books", "Google Books", f"https://www.google.com/search?tbm=bks&q={q}")
        )
    goodreads_id = external.get("goodreads", "")
    if _GOODREADS_ID.match(goodreads_id):
        links.append(
            _direct(
                "goodreads",
                "Open on Goodreads",
                f"https://www.goodreads.com/book/show/{goodreads_id}",
            )
        )
    else:
        links.append(_search("goodreads", "Goodreads", f"https://www.goodreads.com/search?q={q}"))
    domain = _AMAZON_DOMAINS.get(country, "amazon.com")
    amazon_q = quote_plus(isbn13) if isbn13 and _ISBN13.match(isbn13) else q
    links.append(_search("amazon", "Amazon", f"https://www.{domain}/s?k={amazon_q}"))
    links.append(_search("open_library", "Open Library", f"https://openlibrary.org/search?q={q}"))
    return links


def platform_links(
    title: str,
    entity_type: EntityType,
    *,
    country_code: str | None = None,
    year: int | None = None,
    external: Mapping[str, str] | None = None,
    isbn13: str | None = None,
    song_title: str | None = None,
    creator: str | None = None,
    store_url: str | None = None,
) -> tuple[PlatformLink, ...]:
    """The links for an item, best first: the first one is the card's main button.

    For a song favourite, `title` is the singer and `song_title` the song, so music links search
    for both. For a song card, `title` is the song, `creator` its artists and `store_url` its
    Apple Music page. External IDs and URLs are used only when they look valid, so nothing odd
    reaches a link.
    """
    name = " ".join(title.split())
    ids = external or {}
    country = _country(country_code)
    match entity_type:
        case EntityType.ARTIST:
            query = f"{song_title} {name}" if song_title else name
            # A song search finds the song; an artist search finds their best-known songs.
            links = _music_links(query if song_title else f"{name} songs", ids)
            if song_title:
                links = [link for link in links if link.kind == "search"]
            return tuple(links)
        case EntityType.MOVIE | EntityType.TV_SHOW:
            return tuple(_screen_links(name, year, country, ids))
        case EntityType.BOOK:
            return tuple(_book_links(name, country, ids, isbn13))
        case EntityType.SONG:
            return tuple(_song_links(name, creator, store_url))
