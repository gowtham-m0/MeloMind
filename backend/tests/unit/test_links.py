"""Tests for platform links: honest labels, valid IDs only, proper encoding, country handling."""

from urllib.parse import parse_qs, urlparse

from app.domain.links import platform_links
from app.domain.models import EntityType

SPOTIFY_ID = "7Ln80lUS6He07XvHI8qqHH"


def test_an_artist_with_a_spotify_id_listens_on_spotify_first() -> None:
    links = platform_links("Arctic Monkeys", EntityType.ARTIST, external={"spotify": SPOTIFY_ID})

    assert links[0].label == "Listen on Spotify"
    assert links[0].kind == "direct"
    assert links[0].url == f"https://open.spotify.com/artist/{SPOTIFY_ID}"
    assert [link.platform for link in links[1:]] == ["youtube", "youtube_music", "apple_music"]


def test_search_links_say_search_never_watch() -> None:
    links = platform_links("Interstellar", EntityType.MOVIE, country_code="IN", year=2014)

    searches = [link for link in links if link.kind == "search"]
    assert searches
    assert all(link.label.startswith("Search on ") for link in searches)
    assert links[0].platform == "justwatch"
    assert links[0].url.startswith("https://www.justwatch.com/in/search?q=")


def test_a_netflix_id_gives_a_direct_link_and_drops_the_netflix_search() -> None:
    links = platform_links(
        "Dark", EntityType.TV_SHOW, external={"netflix": "80100172", "imdb": "tt5753856"}
    )

    platforms = [link.platform for link in links]
    assert links[0].label == "Open on Netflix"
    assert links[0].url == "https://www.netflix.com/title/80100172"
    assert platforms.count("netflix") == 1
    assert any(link.url == "https://www.imdb.com/title/tt5753856/" for link in links)


def test_invalid_external_ids_are_ignored() -> None:
    links = platform_links(
        "Odd",
        EntityType.MOVIE,
        external={"netflix": "1/../evil", "imdb": "javascript:alert(1)"},
    )

    assert all(link.kind == "search" for link in links)
    assert not any("evil" in link.url or "javascript" in link.url for link in links)


def test_titles_are_url_encoded() -> None:
    links = platform_links("Kapoor & Sons", EntityType.MOVIE, country_code="IN")

    netflix = next(link for link in links if link.platform == "netflix")
    assert parse_qs(urlparse(netflix.url).query) == {"q": ["Kapoor & Sons"]}
    assert " " not in netflix.url


def test_books_use_the_isbn_and_the_country_amazon() -> None:
    links = platform_links(
        "Normal People",
        EntityType.BOOK,
        country_code="IN",
        isbn13="9780571334650",
        external={"goodreads": "41057294"},
    )

    assert links[0].url == "https://books.google.com/books?vid=ISBN9780571334650"
    assert any(link.label == "Open on Goodreads" for link in links)
    amazon = next(link for link in links if link.platform == "amazon")
    assert amazon.url == "https://www.amazon.in/s?k=9780571334650"


def test_unknown_countries_fall_back_to_the_us() -> None:
    links = platform_links("Her", EntityType.MOVIE, country_code="??")

    assert links[0].url.startswith("https://www.justwatch.com/us/")


def test_a_song_favourite_searches_the_song_and_singer() -> None:
    links = platform_links(
        "Glass Animals",
        EntityType.ARTIST,
        song_title="Heat Waves",
        external={"spotify": SPOTIFY_ID},
    )

    assert all(link.kind == "search" for link in links)
    assert "Heat+Waves+Glass+Animals" in links[0].url


def test_a_song_listens_on_apple_music_first_then_searches_by_title_and_artist() -> None:
    links = platform_links(
        "Paper Moons",
        EntityType.SONG,
        creator="The Lanterns",
        store_url="https://music.apple.com/us/album/first-light/1?i=2",
    )

    assert links[0].label == "Listen on Apple Music"
    assert links[0].kind == "direct"
    assert all(link.label.startswith("Search on") for link in links[1:])
    assert "Paper+Moons+The+Lanterns" in links[1].url


def test_a_song_store_url_off_apple_music_becomes_a_search() -> None:
    links = platform_links(
        "Paper Moons", EntityType.SONG, creator="The Lanterns", store_url="https://evil.test/x"
    )

    assert links[0].label == "Search on Apple Music"
    assert all("evil.test" not in link.url for link in links)
