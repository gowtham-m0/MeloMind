# MeloMind

MeloMind helps families and caregivers of people living with dementia share personal music and memory sessions.

- **The caregiver** enters a few things the person loved when they were young. A birth year and a hometown are enough to start.
- **An AI agent** uses [Qloo](https://qloo.com)'s taste graph to find songs, films, TV shows and books from the person's youth, and builds sessions of about 20 minutes with a reason for every pick and gentle conversation prompts.
- **The person** chooses what to play by tapping large cards in Person mode. The AI never talks to them, and the caregiver approves everything they see.
- **The Memory Graph** keeps the memories that come up as linked notes about people, places, songs and decades.

Built for the Qloo Agentic Hackathon.

## Tech stack

| Area | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, uv |
| Agent | LangGraph, with LangChain `create_agent` for the research step |
| Database and auth | Supabase (Postgres, anonymous sign-in) |
| Frontend | React 19, Vite, TypeScript, React Router, TanStack Query, Tailwind and shadcn/ui |
| Media | YouTube Data API and IFrame Player |

## Repo layout

```
backend/    FastAPI app (layered: core, domain, application, infrastructure, api)
frontend/   React app (app, pages, features, shared)
docs/       plan, phases, API contract
```

## Run it locally

You need [uv](https://docs.astral.sh/uv/) and Node 22.22 or later.

**Backend** (http://localhost:8000/docs)

```bash
cd backend
uv sync
cp .env.example .env    # optional: leave QLOO_API_KEY empty to use demo data
uv run uvicorn app.main:app --reload
```

**Frontend** (http://localhost:5173)

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The home page should show "Backend: ok" and "Demo data".

## Checks

```bash
# backend
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest

# frontend
cd frontend && npm run lint && npm run build
npm run gen:api    # regenerate API types while the backend is running
```

## Docs

- [Plan, decisions and risks](docs/PLAN.md)
- [Phases](docs/phases/PHASES.md)
- [API contract](docs/API_CONTRACT.md)
- [Agent design](docs/AGENT.md)
- [Qloo notes](docs/QLOO_NOTES.md)
- [How we work with Claude Code](CLAUDE.md)

## License

[MIT](LICENSE)
