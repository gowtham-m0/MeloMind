# Qloo notes

What we know about the Qloo API, what we've checked, and how our adapter uses it.
Owner: the agent owner. Sources: the **hackathon guide** (Qloo's hackathon API page), Qloo's public reference at
[docs.qloo.com](https://docs.qloo.com/reference/api-overview), and **live test calls with the
hackathon key on 23 Oct 2026**. Markers: *(live)* = checked with a real call; *(hackathon)* = from
the hackathon guide; *(docs)* = from the public reference; *(unverified)* = our best guess.

Rule 12 applies to this file: record response **shapes** (field names and types) and yes/no
findings, never real responses or real entity IDs.

---

## 1. Calling it

- **Base URL:** `https://hackathon.api.qloo.com`, always with a path. The hackathon key returns
  401 on `api.qloo.com` and `staging.api.qloo.com`, which the public docs' examples use
  *(hackathon)*.
- **Auth:** `X-Api-Key: <key>` header *(live)*. Not a query parameter, not a Bearer token. A
  missing header returns 401 "No API key found in request" *(hackathon)*.
- **Method:** GET with query parameters only *(live)*. A POST with a JSON body fails *(hackathon)*,
  so the public docs' POST-only inputs (weighted signals, `*.query` arrays) are off-limits.
- **List values:** comma-separated in one parameter, e.g. `signal.interests.entities=id1,id2`.
- **Entity IDs** are UUID-style strings *(live)*.
- **Errors** (handle them all in the live adapter):

  | Status / message | Meaning | Our handling |
  |---|---|---|
  | 401 | Wrong host or missing key *(hackathon)* | Config error; log it, use fixtures for this run |
  | 403 "You do not have permission to access urn:entity:…" | Entity type not supported *(hackathon)* | Bug on our side; never retry |
  | 400 "at least one valid signal or filter is required" | Tag or audience IDs weren't valid *(hackathon)* | Treat as an empty result; try the next query |
  | 200 with empty results | A parameter was silently dropped or had a bad value, or no data *(live)* | Next rung or fallback; log it |
  | 404 "No results" | No match *(docs)* | Treat as "no match" from `/search` |
  | 429, 5xx | Rate limit or server error *(docs)* | Retry with backoff |

## 2. Endpoints we use

| Endpoint | Use | Checked |
|---|---|---|
| `GET /search` | Names to entity IDs (favourites, the hint ladder). Params: `query`, `types`, `take` | ✓ *(live)* |
| `GET /entities` | Details for IDs we already hold. Param: `entity_ids` | not yet |
| `GET /v2/insights` | Recommendations. **`filter.type` is required** | ✓ *(live)* |
| `GET /v2/tags` | Tag IDs for `signal.interests.tags`. Params: `filter.query`, `take` | ✓ *(live)* |
| `GET /v2/analysis/compare` and `GET /v2/insights/compare` | Taste page tags and Taste match (Phase 4). Params: `a.signal.interests.entities`, `b.signal.interests.entities`, `take` | ✓ *(live)*: **both paths work** and return the same shape |

- **Compare returns tags, not recommendations** *(live)*: for each group, the tags that describe
  it, plus shared tags. Taste match uses the shared tags as `signal.interests.tags` in a normal
  insights call to find items both sides may enjoy.
- **Never call** `/recommendations` or `/recs`.

## 3. `/v2/insights` parameters we use

Entity types: `urn:entity:artist`, `urn:entity:movie`, `urn:entity:tv_show`, `urn:entity:book`.
Qloo has **no song type and no lyrics**. A song is stored as text, and its singer, composer or
film is the signal. Never send a song title or a lyric to Qloo.

| Parameter | Artist | Movie | TV | Book | Live result (23 Oct) |
|---|:-:|:-:|:-:|:-:|---|
| `filter.type` | ✓ | ✓ | ✓ | ✓ | Required |
| `signal.interests.entities` | ✓ | ✓ | ✓ | ✓ | Works across types (an artist signal gives sensible films and books) |
| `signal.interests.tags` | ✓ | ✓ | ✓ | ✓ | Works with IDs from `/v2/tags` (`urn:tag:genre:music:…`) |
| `signal.demographics.age` | ✓ | ✓ | ✓ | ✓ | Works: `55_and_older` vs `24_and_younger` visibly changes artist results |
| `filter.release_year.min` / `.max` | ✗ | ✓ | ✓ | ✗ | Works |
| `filter.publication_year.min` / `.max` | ✗ | ✗ | ✗ | ✓ | Works |
| `filter.release_country` | ✗ | ✓ | ✓ | ✗ | **Needs the full country name** (`United States`, `India`). ISO codes (`US`, `IN`) and `USA` return **nothing**, silently |
| `filter.popularity.min` | ✓ | ✓ | ✓ | ✓ | Works (0–1) |
| `filter.exclude.entities` | ✓ | ✓ | ✓ | ✓ | Works: the excluded item disappears |
| `filter.results.entities` | ✓ | ✓ | ✓ | ✓ | **Works**: returns only the given IDs of that type, each with an affinity. The taste quiz uses it |
| `take` | ✓ | ✓ | ✓ | ✓ | **Default is 20, not 5**. Honoured up to 50 |

**Artists have no era filter.** Learned from the live calls:
- With **no entity signal**, artists ignore the era completely: the age signal alone returns
  today's biggest bands (2000s rock). So a cold start with nothing **must not** ask for artists
  that way.
- Artists **do** come out right when the signal is from their era: an era film, an era artist, or
  an era/genre tag (`urn:tag:genre:music:60s`, `urn:tag:genre:music:tamil`). So for the
  `throwback` row and a cold start, first get films (they have a year and country filter), then
  use those films as the signal for artists.
- Films, TV and books with only the age signal, the era and a popularity floor work fine: no error,
  and they return big hits from those years.

**Books steer books only** *(live, 24 Oct)*. A book in `signal.interests.entities` works for
`filter.type=urn:entity:book`, but for artists, films and TV Qloo returns **400** "All of the
provided signal.interests.entities were invalid". Artists, films and TV work as signals for every
type. So `get_insights` drops book signals for other types, and the cross-culture rail uses the
newest artist, film or show.

The adapter's `InsightsQuery` maps only to the parameters in this table. Anything else is
rejected in code, never passed through. The adapter converts our ISO `country_code` to the full
English country name for `filter.release_country`.

## 4. Gotchas

- **Invalid parameters are silently ignored** *(live)*: `filter.not_a_param=1` changed nothing.
  A bad *value* is worse: an ISO country code silently returns an empty list.
- **`take`:** default 20, maximum 50 *(live)*. Always set it.
- **Search is fuzzy in odd ways** *(live)*: names with initials and spaces often fail
  ("T. M. Soundararajan" matched "T.M.Revolution"), and the top result can be a different entity
  with a similar name ("P. Susheela" → also "P!nk"). The resolver must check name, type and year,
  never just take the first result.
- **Remakes share titles** *(live)*: "Kadhalikka Neramillai" finds the 2025 film first and the 1964
  original under the spelling "Kadalikka Neramillai". The year check matters.
- **Artists have no year** in `/search` or insights *(live)*. Films have `properties.release_year`;
  books have `properties.publication_year`.
- **Books often have no `popularity`** in `/search` results *(live)*, though they do in insights.
  Treat it as optional.
- **`akas`** (alternative names) exists on artists and films *(live)* but was empty in our samples.
  Don't rely on it.
- **Tags must be real tag IDs** from `/v2/tags`, never free text *(hackathon)*. The tag's ID field
  is `id`, not `tag_id` *(live)*.
- **Insights `type` is just `urn:entity`**; the real type is in `subtype` (`urn:entity:movie`)
  *(live)*.
- **Sparse data** for some regions *(hackathon, live)*: see section 5.
- **Cache on the server**, in `qloo_cache`. Private server-side caching is allowed with no time
  limit; Qloo data in a public repo is not *(hackathon)*.
- **Quotas:** high, and can be raised in `#api-help` on the Qloo Hackathon Discord *(hackathon)*.
- **Key lifetime:** active through the end of judging, then deactivated *(hackathon)*. The fixtures
  keep the app and the tests working without it.

## 5. Coverage check (23 Oct)

*Written for the old dementia demo profiles (1960s US and Tamil). Still useful as a record of
regional coverage. The new demo profiles (Aanya: 2010s–2020s indie, India; Leo: classic film
and jazz, US) need their own check in Phase 2, including image coverage.*

**Margaret** (1960s US): **excellent.** All four favourites are found first try. Insights from
The Supremes give Motown artists, 1960s musicals, 1960s US TV and 1960s novels.

**Lakshmi** (1960s Tamil): **partial.**

| Favourite / related | In Qloo? |
|---|---|
| P. Susheela (singer) | ✓ found (low popularity) |
| S. Janaki, S. P. Balasubrahmanyam, Ilaiyaraaja, T. K. Ramamoorthy | ✓ found |
| T. M. Soundararajan (singer of her song favourite) | ✗ not found under any spelling |
| M. S. Viswanathan (composer) | ✗ not found under any spelling |
| K. V. Mahadevan, L. R. Eswari, Sirkazhi Govindarajan | ✗ not found |
| Kadhalikka Neramillai (1964) | ✓ found, as "Kadalikka Neramillai" |
| Paasa Malar (1961) | ✓ found, as "Pasamalar" |
| Thillana Mohanambal, Server Sundaram, Thiruvilaiyadal ("Thiruvilayadal") | ✓ found |
| Ponniyin Selvan (book) | ✓ found |

- Films from her era with `filter.release_country=India` come back mostly as **Hindi and Bengali**
  films, not Tamil. A Tamil film as the signal works better (Kadalikka Neramillai → Anbe Vaa).
- An artist signal like P. Susheela without an era gives **modern** Tamil films (2019–2023), so
  films must always carry the era filter.

This made a good hint-ladder demo: singer T. M. Soundararajan → not found; composer
M. S. Viswanathan → not found; the film the song comes from, Pasamalar (1961) → found ✓. Keep it
as a resolver test case.

**Live run, 24 Oct** (profile with One Direction, The Strokes, Glass Animals): insights gave
Lorde, The 1975, Arctic Monkeys and Two Door Cinema Club for artists, and 2016–2024 films and TV
with an Indian lean from the country. The Qloo side was good; the YouTube lookups were not (Shorts,
ranking clips), which led to the pivot.

## 6. Images, external IDs and ISBNs *(live, 24 Oct)*

Checked with 3 searches and 20 insights results per type. Field names and coverage only.

| Field | Search | Insights | Shape | Our use |
|---|---|---|---|---|
| `properties.image.url` | 3/3 every type | 20/20 every type | `{ "url": "https://images.qloo.com/…" }` | `image_url` on every card |
| `properties.isbn13` | 2/3 books | 18/20 books | string | Google Books link; Open Library cover only as a fallback |
| `properties.description` / `short_description` | films, TV, books / artists, some books | 20/20 | string | The detail view |
| `tags` | yes (`tag_id`, `name`, `type`, `value`) | 19–20/20 (`id`, `name`, `type`) | list | Card chips: prefer `urn:tag:genre:*` names |
| `external` | inside `properties`, 3/3; **values are objects** `{ "id": … }` | top level, 20/20; **values are lists** `[{ "id": … }]` | see below | Direct platform links |

`external` keys seen:
- **Artists:** `spotify` (22-character ID, 10/10), `lastfm`, `musicbrainz`, `wikidata`, `imdb`, `facebook`, `instagram`, `twitter`.
- **Films and TV:** `imdb` (`tt…`), **`netflix`** (numeric ID, 10/10 for a sci-fi film signal), `letterboxd`, `metacritic`, `rottentomatoes`, `wikidata`.
- **Books:** `goodreads` (ID plus ratings).

So direct links are common: Spotify for artists, Netflix and IMDb for films and TV, Goodreads for books. The adapter normalises both shapes to `{ platform: id }`, taking the first ID.

**Caution:** a Netflix ID means the title is on Netflix somewhere, not necessarily in the user's country. Label it "Open on Netflix", and keep JustWatch for "where to watch".

## 7. Response shapes *(live, field names only)*

### `/search`

```jsonc
{
  "results": [
    {
      "entity_id": "string",
      "name": "string",
      "types": ["urn:entity:artist"],
      "popularity": 0.0,          // missing for many books
      "disambiguation": "string",
      "properties": {
        // artist: akas, duration, external, image, short_description   (no year)
        // movie:  release_year, release_date, release_country, akas, content_rating,
        //         description, external, image, production_company, ...
        // book:   publication_year, publication_date, description, format, isbn13, page_count, ...
      },
      "tags": [{ "tag_id": "string", "name": "string", "type": "string", "value": "string" }]
    }
  ]
}
```

### `/v2/insights`

```jsonc
{
  "success": true,
  "results": {
    "entities": [
      {
        "entity_id": "string",
        "name": "string",
        "type": "urn:entity",
        "subtype": "urn:entity:movie",   // the real type
        "popularity": 0.0,
        "properties": { "release_year": 0, "publication_year": 0, "...": "many more" },
        "tags": [],
        "query": { "affinity": 0.0, "measurements": {} },
        "disambiguation": "string",
        "external": {}
      }
    ]
  }
}
```

### `/v2/tags`

```jsonc
{
  "success": true,
  "duration": 0,
  "results": {
    "tags": [
      { "id": "urn:tag:genre:music:…", "name": "string", "type": "urn:tag:genre:music",
        "popularity": 0.0, "parents": [], "properties": {}, "tags": [] }
    ]
  }
}
```

### `/v2/analysis/compare` (same on `/v2/insights/compare`)

```jsonc
{
  "duration": 0,
  "results": {
    "a": [{ "tag_id": "string", "name": "string", "type": "string", "subtype": "string",
            "entity_id": "string", "popularity": 0.0, "query": { "count": 0 } }],
    "b": [ /* same as a */ ],
    "tags": [],            // shared tags
    "matchEntities": []
  }
}
```

## 8. How the adapters map onto this

Both adapters implement the `TasteGraph` port, so the rest of the app never sees a Qloo response.

| Our field (`EntityMatch`) | Live (`QlooHttpTasteGraph`) | Fixture (`FixtureTasteGraph`) |
|---|---|---|
| `entity_id` | `entity_id` | `entity_id` (`demo-…`) |
| `name` | `name` | `name` (search also matches `aliases`) |
| `type` | search: `types[0]`; insights: `subtype` | `type` |
| `release_year` | `properties.release_year`, else `properties.publication_year`, else none | `release_year` |
| `popularity` | `popularity` (optional) | `popularity` |
| `affinity` | `query.affinity` | `insights.json` → `related[signal][].affinity` |
| `image_url` | `properties.image.url` | `image_url` (`null` in fixtures: the UI shows the fallback tile) |
| `external` | `properties.external` (search) or top-level `external` (insights), normalised to `{platform: id}` | `external` |
| `isbn13` | `properties.isbn13` (books) | `isbn13` |
| `tags` | `tags[].name` (up to 4) | `tags` |
| `source` | `qloo_live` | `demo_fixture` |

Fixture details are in `backend/app/infrastructure/qloo/fixtures/README.md`.
