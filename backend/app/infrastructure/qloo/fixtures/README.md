# Demo fixtures

Hand-written demo data for `FixtureTasteGraph`, used when `QLOO_API_KEY` is empty and in all
tests. **This is not Qloo data.** Names are real titles, but every ID, popularity and affinity
here is invented. The UI labels anything from these files "Demo data".

Rules:
- Every file has `"demo": true` at the top level.
- Every ID starts with `demo-`, so a real Qloo ID can never be mistaken for one of these.
- No real Qloo responses, ever (`CLAUDE.md`, rule 12). When the key arrives, record response
  *shapes* in `docs/QLOO_NOTES.md`, not data here.
- No lyrics. Song titles appear only as `song_title` on a favourite.

`tests/unit/test_qloo_fixtures.py` checks all of the above.

## Files

| File | Holds |
|---|---|
| `profiles.json` | The two sample profiles, in the shape of `POST /profiles`, plus favourites by **name**. `demo/seed` resolves each name through `TasteService.search`, so no ID is hard-coded |
| `entities.json` | The catalogue: `entity_id`, `name`, optional `aliases`, `type` (`urn:entity:artist`, `movie`, `tv_show`, `book`), `release_year`, `country` (ISO 3166-1 alpha-2), `popularity` (0–1) and `tags` |
| `insights.json` | `related`: for each favourite's entity, about 15 related entities with an invented `affinity` (0–1), across all four types |
| `tags.json` | Genre and region tags for `find_tags` and the hint ladder's tag step |

`release_year` means the release year for films and TV, the publication year for books, and
roughly the year of the first big hit for artists. Like Qloo, the era filters apply only to
films, TV and books; an artist's year is for display and for the warm-up's "closest year"
fallback.

## The sample profiles

| Profile | Born | Grew up | Era window (`+13` to `+21`) | Favourites |
|---|---|---|---|---|
| Margaret | 1948 | Chicago, US | 1961–1969 | The Supremes; "My Girl" by The Temptations; The Sound of Music; To Kill a Mockingbird (book) |
| Lakshmi | 1950 | Chennai, IN | 1963–1971 | P. Susheela; "Malarnthum Malaraatha" sung by T. M. Soundararajan; Kadhalikka Neramillai; M. S. Viswanathan |

## Edge cases built in

- **Spelling variants** (hint ladder step 3): `aliases` such as "P Susheela", "TMS", "MSV",
  "Ilayaraja", "Kathalikka Neramillai".
- **Same name, different type:** "To Kill a Mockingbird" is both a book and a film, and
  "Malgudi Days" both a book and a TV show. The resolver must check the type, not only the name.
- **Just outside the era**, for the fallback's ±5-year relaxation: Some Like It Hot (1959),
  Hawaii (1959), American Bandstand (1957), Kalyana Parisu (1959).
- **Far outside the era**, which no relaxation should reach: Singin' in the Rain, I Love Lucy,
  Gone with the Wind, Parasakthi, Ramayan.
- **Low popularity**, for the popularity floor: Shindig!, The Chi-Lites, Oliyum Oliyum,
  Chithirappavai, A. M. Rajah.
- **Thin coverage, on purpose:** Lakshmi has no TV inside her era and only two books, as we
  expect from Qloo for older Tamil titles. Plans for her must still fill a session.
- **Exclusions:** any ID works. Tests usually exclude `demo-artist-the-temptations`, which
  appears in two of Margaret's insight lists.
