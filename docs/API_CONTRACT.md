# API contract

The backend's HTTP API. B leads this file and A reviews it. Update it in the same PR as any endpoint change, then run `npm run gen:api` in `frontend/`.

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
