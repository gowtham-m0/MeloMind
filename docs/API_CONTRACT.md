# API contract

The backend's HTTP API. The backend owner leads this file and the frontend owner reviews it. Update it in the same PR as any endpoint change, then run `npm run gen:api` in `frontend/`.

## Conventions

- Every route lives under `/api/v1`. JSON uses snake_case.
- Every route except health sends `Authorization: Bearer <Supabase access token>`.
- Application errors return `{ "error": "<code>", "detail": "<message>" }`:

| Status | `error` | When |
|---|---|---|
| 404 | `not_found` | The resource doesn't exist, or belongs to someone else |
| 422 | `invalid_input` | The request is well-formed but breaks a rule |
| 502 | `upstream_error` | Qloo, YouTube or the LLM failed or timed out |
| 500 | `internal_error` | Anything unexpected. Responses never include stack traces |

Unknown routes and request validation errors keep FastAPI's default shape: `{ "detail": ... }` only, where `detail` is a list for validation errors.

## Phase 0

### `GET /api/v1/health`

No auth. Response `200`:

```json
{ "status": "ok", "app_name": "MeloMind", "env": "development", "qloo_mode": "demo_fixtures" }
```

- `status`: always `"ok"`.
- `env`: the `APP_ENV` setting.
- `qloo_mode`: `"live"` when `QLOO_API_KEY` is set, otherwise `"demo_fixtures"`.

## Phase 1

Every route below needs `Authorization: Bearer <Supabase access token>`. A missing, expired or
invalid token returns `401` with `{ "error": "unauthorized", "detail": "..." }`. So does every
request when the backend has no `SUPABASE_URL`.

Profile-scoped routes check ownership: someone else's profile (or favourite) is a `404`
`not_found`, exactly like one that doesn't exist.

### Types

`Profile`:

```json
{
  "id": "uuid",
  "display_name": "Margaret",
  "birth_year": 1948,
  "country_code": "US",
  "places_lived": ["Chicago, Illinois"],
  "languages": ["English"],
  "is_demo": true,
  "favourites": [Favourite]
}
```

- `display_name`: 1–60 characters, trimmed. Required.
- `birth_year`: 1920–1990. Required.
- `country_code`: where they grew up, ISO 3166-1 alpha-2, upper-cased by the backend; or `null`.
- `places_lived`, `languages`: up to 10 strings of up to 100 characters. The first place is the
  hometown. Default `[]`.
- `favourites`: oldest first.

`Favourite`:

```json
{
  "id": "uuid",
  "name": "The Temptations",
  "kind": "song",
  "qloo_id": "string or null",
  "verified": true,
  "song_title": "My Girl"
}
```

- `kind`: `artist`, `song`, `movie`, `tv_show` or `book`.
- `name`: for a song, the singer.
- `verified`: true when `qloo_id` is set, i.e. the caregiver picked a taste-search match. Only
  verified favourites become Qloo signals.
- `song_title`: only for `kind: "song"`, otherwise `null`.

### `POST /api/v1/demo/seed`

No body. `200`: `{ "profile_ids": ["uuid", "uuid"] }`. Creates the sample profiles for this user
the first time; later calls return the existing demo profile IDs and change nothing. Favourites
are resolved by name through taste search; any that don't match exactly, or if search fails,
are kept as text (`verified: false`).

### `GET /api/v1/profiles`

`200`: `Profile[]`, the user's profiles, oldest first.

### `POST /api/v1/profiles`

Body: `{ "display_name", "birth_year", "country_code"?, "places_lived"?, "languages"? }`.
`201`: `Profile`. Validation failures are `422` with FastAPI's default shape.

### `GET /api/v1/profiles/{id}`

`200`: `Profile`. `404` if missing or not yours.

### `PATCH /api/v1/profiles/{id}`

Body: any profile fields. Fields left out are unchanged. `"country_code": null` clears it;
`null` for `display_name`, `birth_year`, `places_lived` or `languages` is a `422`. `200`: `Profile`.

### `DELETE /api/v1/profiles/{id}`

`204`. Deletes the profile and everything that belongs to it.

### `GET /api/v1/taste/search?q=&type=`

- `q`: 1–100 characters (blank after trimming is a `422`).
- `type` (optional): a favourite kind. `song` searches **artists**: search for the singer, never
  the song title. Without `type`, all four entity types are searched.

`200`: up to 8 matches:

```json
[{ "entity_id": "string", "name": "The Supremes", "type": "artist", "release_year": null }]
```

- `type`: `artist`, `movie`, `tv_show` or `book`.
- `release_year`: release year for films and TV, publication year for books; `null` for artists.
- Results come from live Qloo or the demo fixtures; `GET /health`'s `qloo_mode` says which.
- `502` `upstream_error` if Qloo fails after retries.

### `POST /api/v1/profiles/{id}/favourites`

Body: `{ "name", "kind", "entity_id"?, "song_title"? }`.

- `name`: 1–120 characters. `entity_id`: the `entity_id` of the search match the caregiver
  picked, or omitted to keep it as text. `song_title`: only with `kind: "song"`, else `422`.
- Saving the same favourite again returns the existing one.

`201`: `Favourite`.

### `DELETE /api/v1/profiles/{id}/favourites/{favourite_id}`

`204`. `404` if the favourite isn't on that profile.
