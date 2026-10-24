# MeloMind

**Your taste, in one home screen.** MeloMind is a personal culture companion for music, films, TV shows and books. Open it the way you open YouTube, Spotify or Netflix, and you get one feed built around what you love, with a reason for every pick and a link straight to where it lives.

- **A feed that explains itself.** A hero pick, "Recommended for you", "Because you liked…", music, films, TV, books and "Popular in your country". Every card has a thumbnail and a one-line reason.
- **Cross-culture picks.** You like a band, so here's a film, a show and a book that share its taste, powered by [Qloo](https://qloo.com)'s cross-domain taste graph.
- **Open it where it lives.** Music opens on YouTube or Spotify, films and shows on JustWatch (which lists Netflix, Prime Video, JioHotstar and the rest for your country), books on Google Books or Goodreads.
- **Your taste updates.** Like, save, open or dismiss, then refresh: the feed changes and the agent log tells you why.
- **A journal you can talk to.** Write or speak about your day. The agent spots the artists, films and books you mention; you confirm them, and they shape your feed.
- **Your taste page.** Your taste in a sentence, top tags, and a map of how your likes connect.

An AI agent built with LangGraph does the work: it chooses its own Qloo calls, recovers from empty results, and writes every step to a plain-English log.

Built for the Qloo Agentic Hackathon.

## Tech stack

| Area | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, uv |
| Agent | LangGraph, with LangChain `create_agent` for the research step; Gemini (main) and Groq (fallback); Groq Whisper for speech |
| Database and auth | Supabase (Postgres, anonymous sign-in) |
| Frontend | React 19, Vite, TypeScript, React Router, TanStack Query, Tailwind and shadcn/ui |
| Taste data | Qloo Insights API |

## Repo layout

```
backend/         FastAPI app (layered: core, domain, application, infrastructure, api)
frontend/        React app (app, pages, features, shared)
docs/            plan, phases, API contract, agent design, Qloo notes
.claude/skills/  shared design skills (impeccable, Emil Kowalski's skills)
image.png        reference mockup for the feed layout
```

## Run it locally

You need [uv](https://docs.astral.sh/uv/) and Node 22.22 or later.

**Backend** (http://localhost:8000/docs)

```bash
cd backend
uv sync
cp .env.example .env    # optional: leave QLOO_API_KEY empty to use demo data
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

**Frontend** (http://localhost:5173)

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Tap **Try the demo** to open a sample profile.

## Checks

```bash
# backend
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest

# frontend
cd frontend && npm run lint && npm run build
npm run gen:api    # regenerate API types while the backend is running
```

## Docs

- [Plan, decisions and risks](docs/PLAN.md) (section 0 explains the pivot of 24 Oct)
- [Phases](docs/phases/PHASES.md)
- [API contract](docs/API_CONTRACT.md)
- [Agent design](docs/AGENT.md)
- [Qloo notes](docs/QLOO_NOTES.md)
- [How we work with Claude Code](CLAUDE.md)

## License

[MIT](LICENSE). The design skills in `.claude/skills/` keep their own licences (Apache 2.0 for impeccable; see each folder).
