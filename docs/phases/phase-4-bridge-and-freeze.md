# Phase 4: Polish and freeze

**Dates:** Thu 29 Oct · **Hours:** about 6 each · **Previous:** [Phase 3](phase-3-memory-graph.md) · **Next:** [Phase 5: Ship](phase-5-ship.md)

**Goal:** finish the right rail's agentic actions, polish every screen to a judge-ready finish, write the end-to-end test, freeze features on Thursday night, then deploy once.
- **Your vibe today** and **Surprise me** in the right rail, and **Ask the agent** in the top bar.
- **Taste match** between two profiles (Qloo compare).
- A full polish pass with the design skills.
- The How it works page.

**Before you start:** Phase 3's exit check has passed. Read `CLAUDE.md` and `docs/PLAN.md` (the judge path and the cut lines).

> This file replaces the old "Bridge and freeze" phase. Bridge's idea (two tastes, Qloo compare, shared picks) lives on as **Taste match**.

---

## First: agree the contract (all three, 15 minutes)

The full shapes are in `docs/API_CONTRACT.md`, "Phase 4: polish".

| Route | Request | Response |
|---|---|---|
| `POST /api/v1/profiles/{id}/ask` | `{ text?, mood?, kind? }` | `{ agent_run_id }`; the run's `result` is one extra row |
| `POST /api/v1/profiles/{id}/taste-match` | `{ other_profile_id }` or `{ favourites }` | `{ shared_tags, score, row }` |

---

## Agent: ask, vibe, surprise, taste match (≈ 6 h)

### Agent 1. Ask the agent
- A short research run with the user's text as an extra instruction in the brief, plus the usual signals and exclusions. The agent may use `find_tags` to turn words like "lighter" or "90s" into real tag IDs.
- The result is one row (`key: "ask"`), with reasons. Same guardrails as the feed.
- The log shows how the request changed the queries ("Turned 'lighter' into the tags Feel-good and Comedy").

### Agent 2. Your vibe today
- Each mood maps to a small set of tag searches (`find_tags`): chill → "chill", "ambient", "slow burn"; happy → "feel-good", "upbeat"; focused → "instrumental", "minimal"; melancholy → "melancholic", "bittersweet"; energetic → "high energy", "action".
- The tags and the user's strongest signals feed one insights call per type. The row title is "Chill picks for you".

### Agent 3. Surprise me
- Pick the type the user engages with least, use one strong signal from another type, and take high-popularity items with lower affinity, so it stays good but new.
- Reason template: "A wildcard: popular with people who like X".

### Agent 4. Taste match
- `compare_tastes(group_a, group_b)` with the strong signals of two profiles (or a friend's 3–5 favourites).
- Score from the share of shared tags; the shared tags then become `signal.interests.tags` for a "For you both" row.

### Agent 5. Tests
- Ask, vibe and surprise apply exclusions and never return items already in the feed.
- An unknown mood is a `422`; an LLM failure in ask falls back to using the text as a tag search.
- Taste match with no shared tags returns score 0 and a popular row, with a log line saying so.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("The agent") and docs/API_CONTRACT.md (Phase 4). Add an ask run that
reuses the research step with the user's text as an extra brief instruction (find_tags
to map words to tags), a mood mapping for "Your vibe today", a surprise mode (least-used
type, lower affinity, high popularity), each returning one guarded row with reasons,
and a taste match using compare_tastes and the shared tags as signals. Tests:
exclusions apply, no duplicates with the feed, unknown mood 422, LLM failure falls
back, no shared tags handled. Run ruff and pytest.
```

**Check:** "Something like Interstellar but lighter" returns a sensible row, and the log shows the tags it used.

---

## Backend: routes, end-to-end test, deploy (≈ 6 h)

### Backend 1. Routes
- `POST /ask` (rate limited with feed builds) and `POST /taste-match`, with ownership checks.

### Backend 2. Playwright end-to-end test
- It covers the judge path (`docs/PLAN.md`, section 6), steps 1–7.
- **In CI:** run it against a local stack in demo mode. With no keys, that means fixtures and templates, so no live services are called. (Voice is skipped in CI; the test types the entry.)
- **By hand:** run it against the live site after the deploy in Backend 3.

**Prompt for Claude Code:**
```
Read CLAUDE.md and docs/API_CONTRACT.md (Phase 4). Add the ask and taste-match routes
with ownership checks and the shared rate limit. Write a Playwright test in e2e/ for
the judge path in docs/PLAN.md (steps 1-7, typing the journal entry), runnable against
a local stack in demo mode (no keys) in CI, and against any base URL passed in (for the
live URL, by hand, after the deploy). Run ruff, pytest and the Playwright test locally.
```

**Check:** the Playwright test passes locally in demo mode.

### Backend 3. Deploy (Thursday night, after the feature freeze)

Do this only when the exit check below passes locally. This is the first deployment, so keep Friday free as the buffer. If anything here fails, fix it before anything else.

**Backend: AWS Lightsail container service**
1. Use the personal AWS account, region `ap-south-1`. Create an **IAM user limited to Lightsail** and use it for the CLI, not the root account.
2. Set an **AWS Budgets alert** (for example $10).
3. Create a container service, **Nano or Micro** size, scale 1.
4. Build the Docker image from `backend/Dockerfile` and push it to the service (`aws lightsail push-container-image`).
5. Create the deployment:
   - container port **8000**, public endpoint on that container;
   - environment variables (never in git): `APP_ENV=production`, `FRONTEND_ORIGIN` (the Vercel URL), `DATABASE_URL`, `SUPABASE_URL`, `QLOO_API_KEY`, `QLOO_BASE_URL`, `YOUTUBE_API_KEY` (optional), the `LLM_*` settings, `STT_MODEL`, and the agent, feed and quiz limits from `CLAUDE.md`;
   - health check path **`/api/v1/health`**.
6. Run `alembic upgrade head` against the Supabase database (from your machine, with the production `DATABASE_URL`).
7. Open `https://<service-url>/api/v1/health` and check it says `"live"` for `qloo_mode`.

**Frontend: Vercel**
1. Import the repo, set the root directory to **`frontend/`**.
2. Set `VITE_API_BASE_URL` to the Lightsail URL, plus `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`.
3. Deploy. `vercel.json` (from Phase 0) keeps routes alive on refresh.

**Then**
1. **Restrict CORS** to the Vercel domain: set `FRONTEND_ORIGIN` on Lightsail to it and redeploy.
2. Add the Vercel URL to Supabase's allowed redirect and site URLs if anonymous sign-in complains.
3. Check the microphone works on the live site (it needs HTTPS, which Vercel provides).
4. **Run the Playwright judge path by hand against the live site.**
5. **Run the judge path once yourself on the live site** to warm the Qloo cache.

**Check:** **Try the demo** works on the live site, and the judge path passes there.

---

## Frontend: the rail's actions, taste match, polish (≈ 6 h)

### Frontend 1. Right rail and top bar
- **Your vibe today:** pick a mood, tap "Get recommendations": a new row slides in at the top of the feed with the mood's title and a dismiss button.
- **Surprise me:** same pattern, with a playful but tasteful reveal (use the `animate` skill).
- **Ask the agent:** a field in the top bar or a "✦ Ask" button that opens a small composer with example prompts; the result row appears like the others; the log panel shows how it was understood.

### Frontend 2. Taste match (`/taste/match`)
- Pick another profile (or add a friend's favourites with search).
- A score ring, the shared tags as chips, and the "For you both" row.

### Frontend 3. How it works page
- The agent diagram (one agent, three workflows, the tools).
- The Qloo calls, in plain words.
- Platform links and why they're labelled "Search on".
- Privacy, especially the journal.

### Frontend 4. Polish pass (compulsory, with the design skills)
- `/impeccable critique` and `/impeccable audit` on every screen, then `/impeccable polish`; fix what they find.
- `improve-animations` across the app, then `review-animations`; motion must feel quick and quiet.
- `break-ui` on cards, rows, the hero, the detail sheet and journal entries (long titles, missing images, non-Latin text, empty rows).
- Check phone, tablet and desktop; keyboard; contrast; `prefers-reduced-motion`.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("Design system", "Frontend conventions") and docs/API_CONTRACT.md
(Phase 4). Use the impeccable and Emil Kowalski skills. Make the right rail work:
"Your vibe today" (mood chips, Get recommendations posts to /ask with mood and slides
a dismissible row into the top of the feed), "Surprise me" (kind: surprise) and an
"Ask the agent" composer in the top bar with examples. Build /taste/match (pick a
profile or add favourites, score ring, shared tag chips, "For you both" row) and the
How it works page. Then run impeccable critique, audit and polish on every screen,
improve-animations and review-animations, and break-ui on cards, rows, hero, sheet and
journal entries; fix every finding. Run lint and build.
```

**Check:** every screen passes the skills' reviews, on a phone and a laptop.

---

## Exit check (Thursday night)

Locally (backend also run once from its Docker image):
- "Your vibe today" and "Surprise me" add a row, and the log shows how.
- "Ask the agent" handles "Something like Interstellar but lighter".
- Taste match between Aanya and Leo shows shared tags and a row.
- The polish pass is done, and its summaries are in the PRs.
- The end-to-end test passes locally.

**Then freeze.** From now on, only bug fixes.

**Then the backend owner deploys (Backend 3).** Phase 4 is done when the judge path also passes on the live site. The frontend and agent owners stay online to test it on a phone and to help if the deploy needs a fix.

## If you're behind

- **Cut first:** taste match, then Ask the agent (keep the vibe chips).
- **Then cut:**
  - the How it works page (put the diagram in the README);
  - the end-to-end test in CI (run it by hand instead).
- **Never cut:** the polish pass on the judge path's screens, and **the deploy**.
