# Phase 0: Kickoff and project setup

> **Status: done (23 Oct).** Written before the pivot of 24 Oct to a personal taste dashboard (see `docs/PLAN.md`, section 0). Everything set up here carries over: repo, CI, `Dockerfile`, health route, Supabase, uv and the frontend toolchain. Mentions of caregivers and Person mode below are historical.

**Dates:** Fri 23 Oct · **Hours:** about 4.5 each · **Next:** [Phase 1: Foundations](phase-1-foundations.md)

**Goal:** settle the open decisions, then create the repo, folders, tooling, boilerplate and a backend `Dockerfile`. Everything runs locally. **No business logic, and no deployment** (that happens once, on Thursday night, in Phase 4).

**Before you start:** read `CLAUDE.md` and `docs/PLAN.md`.

---

## Step 1: Kickoff (30 minutes, all three)

1. Settle the open decisions in `docs/PLAN.md`, section 3.
2. Read `CLAUDE.md` together, especially the rules, the "Who does what" table and Person mode.
3. The backend owner creates the repo first. The frontend and agent owners start once it exists, to avoid conflicting scaffolds.
4. Everyone installs Claude Code, Python 3.12 and Node 20+.

---

## Step 2: Project setup

**Order:** the backend's steps 1–3 come first (about an hour). Then the frontend and agent work run in parallel.

### Backend: repo, backend skeleton, CI, Dockerfile (≈ 4 h)

1. **Create the GitHub repo:**
   - public, with an MIT `LICENSE`, a `.gitignore` and a short `README.md`;
   - add `CLAUDE.md`, `docs/PLAN.md` and `docs/phases/`;
   - protect `main`: pull requests only, one review, CI required.
2. **Backend skeleton**, using Claude Code (prompt below).
3. **CI** with GitHub Actions:
   - backend: `ruff` and `pytest`;
   - frontend: `npm ci`, `lint` and `build`, once the frontend scaffold has merged.
4. **`backend/Dockerfile`** and a `.dockerignore`:
   - Python 3.12 slim base, non-root user;
   - install with uv from the lockfile: `uv sync --frozen --no-dev`;
   - start command `uvicorn app.main:app --host 0.0.0.0 --port 8000`;
   - it reads all settings from environment variables, and holds no secrets.
   - Lightsail uses this image in Phase 4, so keep it working.

(The Supabase project is created in Phase 1, when it's first needed.)

**Prompt for Claude Code:**
```
Read CLAUDE.md. Create the backend skeleton for Phase 0, following the "Repo layout"
and "Architecture" sections exactly. Include:
- an app factory in app/main.py
- core/ (settings via pydantic-settings, logging, base errors)
- api/errors.py and api/v1/router.py
- a GET /api/v1/health endpoint returning status, app name, env and qloo_mode
  ("live" if QLOO_API_KEY is set, otherwise "demo_fixtures")
- empty packages for every layer, each with a one-line docstring saying what belongs
  there, including application/agent/workflows/ (plan_session, resolve_favourite,
  link_memory as empty modules) and application/modes/
- pytest with one health test
- a ruff config
- a uv project: pyproject.toml with exact pins (uv add --bounds exact), uv.lock,
  .python-version (3.12); no requirements files
- .env.example listing every backend variable from CLAUDE.md
- backend/Dockerfile and .dockerignore (Python 3.12 slim, non-root, port 8000, settings
  from environment variables only)
No business logic, no database code yet. Run ruff and pytest, build the Docker image,
run it, call /api/v1/health, and show me the output.
```

**Check:**
- `/api/v1/health` works on `localhost:8000`, both with `uvicorn` and in the Docker container.
- CI is green on a test pull request.

### Frontend: frontend skeleton (≈ 4 h)

1. **Frontend skeleton**, using Claude Code (prompt below). It has two layouts:
   - the **caregiver layout**, with navigation;
   - the **Person layout**: full screen, with no navigation and no way out except a placeholder for the caregiver unlock.
2. **API type generation:**
   - add an `npm run gen:api` script that runs `openapi-typescript` against the backend's `/openapi.json`;
   - it writes `src/shared/api/schema.d.ts`.
3. **`frontend/vercel.json`** with an SPA rewrite, so routes survive a refresh. Vercel uses it in Phase 4.
4. **Local env:** a `frontend/.env.example` with `VITE_API_BASE_URL=http://localhost:8000`.

**Prompt for Claude Code:**
```
Read CLAUDE.md. Create the frontend skeleton for Phase 0 in frontend/: Vite + React 19
+ TypeScript strict, React Router, TanStack Query provider, Tailwind + shadcn/ui,
ESLint + Prettier. Folders: app/, pages/, features/, shared/{api,ui,hooks,types}.
Add a typed API client in shared/api that reads VITE_API_BASE_URL. Add two layouts:
CaregiverLayout (navigation, 18px base font, 44px tap targets, high contrast) and
PersonLayout (full screen, no navigation, a placeholder for the caregiver unlock).
Add placeholder pages and routes: /, /profiles, /profiles/new, /profiles/:id,
/profiles/:id/plan, /profiles/:id/person (PersonLayout), /profiles/:id/memories,
/profiles/:id/memories/:nodeId, /profiles/:id/review, /profiles/:id/bridge,
/sessions/:id, /sessions/:id/play, /how-it-works. The home page calls
/api/v1/health and shows "Backend: ok" plus "Demo data" or "Live Qloo".
Add an npm script gen:api using openapi-typescript. No feature logic. Run lint and
build and show me the output.
```

**Check:** every route on `localhost:5173` survives a refresh (try `npm run build && npm run preview` too), and the home page shows "Backend: ok" from the backend on `localhost:8000`.

### Agent: Qloo notes, agent design, keys and demo data (≈ 4 h)

1. **`docs/QLOO_NOTES.md`:**
   - endpoints, parameters for each entity type, and gotchas, from the Qloo developer guide and parameter guide;
   - a **"To verify" list**:
     - `filter.results.entities` (for warm-up scoring);
     - which entity types accept `signal.demographics.age`;
     - the format `filter.release_country` expects;
     - whether `/v2/insights/compare` works with the hackathon key;
   - a section for the real response shapes.
2. **`docs/AGENT.md`**, for the backend owner to review:
   - all three workflows (plan a session, resolve a favourite, link a memory note) and their steps;
   - the tools, their inputs and outputs, and the limits;
   - the research brief for each mode (`standard`, `warmup`, later `bridge`), including the three cold-start tiers;
   - the hint ladder;
   - the link-extraction output schema;
   - the state fields and the `SessionMode` interface;
   - the fallback and the guardrails;
   - the style for agent log messages.
3. **Hand-written demo fixtures** (data, not code) in `backend/app/infrastructure/qloo/fixtures/`:
   - two sample profiles:
     - Margaret, born 1948, Chicago;
     - Lakshmi, born 1950, Chennai;
   - each with 3–4 favourites, including at least one song title;
   - for each favourite, about 15 related items across artists, films, TV shows and books, spread over the decades of their youth, with release year, popularity and an invented affinity;
   - every file marked `"demo": true`.
4. **Keys:**
   - a Google Cloud project with **YouTube Data API v3** enabled, and an API key restricted to that API;
   - an LLM account with a spending cap, and one test call made locally.
5. **If the Qloo key arrives:** make one `/search` and one `/v2/insights` call with curl, and paste the real response shapes into `QLOO_NOTES.md`.

**Prompt for Claude Code (for the design doc):**
```
Read CLAUDE.md, especially "The agent", "Cold start", "Person mode" and "Memory
Graph". Draft docs/AGENT.md: describe the three workflows (plan_session,
resolve_favourite, link_memory) step by step, with each step's input and output
state fields, what it logs and how it fails. Define each tool (inputs, outputs,
which Qloo endpoint or port, validation), the middleware limits, the research brief
for the standard and warmup modes (with the three cold-start tiers), an outline of
the research agent's system prompt, the hint ladder, the link-extraction output
schema, the SessionMode interface, the rule-based fallback and the guardrails.
Keep it under 4 pages. Don't write code.
```

**Check:** the backend owner has reviewed both docs, the fixtures are committed, and the YouTube and LLM keys work.

---

## Exit check

- The frontend on localhost talks to the backend on localhost, and the backend also runs from its Docker image.
- CI is green.
- The `Dockerfile` and `vercel.json` are in the repo.
- The docs and fixtures are in the repo.
- All three of you have run both apps locally.
