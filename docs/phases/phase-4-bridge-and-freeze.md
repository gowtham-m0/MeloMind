# Phase 4: Bridge and freeze

**Dates:** Thu 29 Oct · **Hours:** about 6 each · **Previous:** [Phase 3](phase-3-memory-graph.md) · **Next:** [Phase 5: Ship](phase-5-ship.md)

**Goal:**
- The Bridge session works: a family visit planned around music both generations enjoy.
- Add the remaining caregiver tools: Ask the agent, swap, "What we learned" and the review queue.
- The end-to-end test passes locally.
- **Feature freeze tonight.**
- **Then deploy, once** (the backend's "Deploy" task). This is the first and only time the app goes on the internet.

**Before you start:** Phase 3's exit check has passed. If it hasn't, skip Bridge and finish Phase 3 first (see "If you're behind").

---

## First: agree the contract (all three, 15 minutes)

| Route | Request | Response |
|---|---|---|
| `POST /api/v1/profiles/{id}/sessions/plan` | `{ mode: "bridge", target_minutes, visitor: { name, relation?, favourites: [{ entity_id, kind, name }] }, instructions? }` | `SessionDraft`, now with `visitor` |
| `POST /api/v1/sessions/{id}/items/{item_id}/swap` | nothing | `SessionDraft` |
| `GET /api/v1/sessions/{id}/learned` | nothing | `{ lines: string[] }` |
| `GET /api/v1/profiles/{id}/review-queue` | nothing | `[{ ref, title, entity_type, hidden_at, note? }]` |
| `POST /api/v1/profiles/{id}/review-queue/{item_ref}` | `{ action: keep_hidden \| show_again \| reject }` | `{ ok }` |

`instructions` is now used by every mode, up to 300 characters.

---

## Agent: Bridge mode, instructions, swap, explanations (≈ 6 h)

### Agent 1. `BridgeMode`
- A research brief that combines the elder's favourites with the visitor's (up to 3), **within the elder's era**.
- A `compare_tastes` tool using `/v2/insights/compare`, if it works with the hackathon key. If not, use two Insights calls and their overlap.
- Prompts are written for the visitor to use. For example: "Ask Grandma where she first heard this."
- Prompts can use confirmed memories with "Use in prompts" on.
- Registered in `ModeRegistry`, with no workflow or API changes.

### Agent 2. Caregiver instructions in the brief
- The agent itself turns a request like "fewer sad songs" or "more film songs" into tags or exclusions.
- The log shows how it did that.

### Agent 3. Swap service
- "Another like this" uses that item as the only signal.
- It excludes the session's current items and the profile's exclusions.
- The guardrails run again.

### Agent 4. Explanations
- **"What changed"** goes into the agent log at the start of each plan.
- **"What we learned"** lines go after each session. For example:
  - "She sang along to X, so Y's music is now a signal."
  - "She chose Z three times in Person mode."
  - "W was rejected and won't come back."

**Prompt for Claude Code:**
```
Read CLAUDE.md ("Session modes", "The agent") and docs/AGENT.md. Add BridgeMode
(research brief combining the elder's favourites with up to 3 visitor favourites
within the elder's era; prompts written for the visitor to ask; may use confirmed,
"Use in prompts" memory nodes) and register it without changing workflows or the
API. Add a compare_tastes tool over /v2/insights/compare, falling back to two
insights calls and their overlap. Pass caregiver instructions into every mode's
brief so the agent maps them to tags or exclusions, and log how. Add a swap service
(one item as the only signal, excluding current items and exclusions, guardrails
re-run). Add "what changed" to the start of each plan's log and "what we learned"
lines per session. Tests with the scripted fake model. Run ruff and pytest.
```

**Check:** a Bridge plan for Margaret with a grandchild's 3 favourites returns shared picks, and the log shows the compare step.

---

## Backend: Bridge storage, routes, review queue, end-to-end test, deploy (≈ 6 h)

### Backend 1. Bridge plan
- The visitor is stored on the session.
- Visitor favourites are verified through search.
- A person node is created for the visitor, linked to the session node, so visits appear in the Memory Graph.

### Backend 2. Instructions and swap
- Validate `instructions` (300 characters at most).
- Add the swap route.

### Backend 3. "What we learned"
- The `learned` route.
- Add the learned lines to the history.

### Backend 4. Review queue API
- **Keep hidden.**
- **Show again:** unhides the item.
- **Never show:** adds an exclusion.

### Backend 5. Playwright end-to-end test
- It covers the judge path (`docs/PLAN.md`), steps 1–6 and 8.
- **In CI:** run it against a local stack in demo mode. With no keys, that means fixtures, templates and the demo media resolver, so no live services are called.
- **By hand:** run it against the live site after the deploy in Backend 6.

**Prompt for Claude Code:**
```
Read CLAUDE.md and docs/API_CONTRACT.md (Phase 4). Extend session planning for
mode "bridge": store the visitor on the session, verify visitor favourites via
TasteService.search, create a person node for the visitor linked to the session
node. Add instructions validation (max 300 chars), the swap route, GET
/sessions/{id}/learned, and the review-queue routes (keep_hidden, show_again
unhides, reject adds an exclusion). Write a Playwright test in e2e/ for the judge
path in docs/PLAN.md (steps 1-6 and 8), runnable against a local stack in demo mode
(no keys) in CI, and against any base URL passed in (for the live URL, by hand, after
the deploy). Run ruff, pytest and the Playwright test locally.
```

**Check:** the Playwright test passes locally in demo mode. (The live-site run comes after Backend 6.)

### Backend 6. Deploy (Thursday night, after the feature freeze)

Do this only when the exit check below passes locally. This is the first deployment, so keep Friday free as the buffer. If anything here fails, fix it before anything else.

**Backend: AWS Lightsail container service**
1. Use the personal AWS account, region `ap-south-1`. Create an **IAM user limited to Lightsail** and use it for the CLI, not the root account.
2. Set an **AWS Budgets alert** (for example $10).
3. Create a container service, **Nano or Micro** size, scale 1.
4. Build the Docker image from `backend/Dockerfile` and push it to the service (`aws lightsail push-container-image`).
5. Create the deployment:
   - container port **8000**, public endpoint on that container;
   - environment variables (never in git): `APP_ENV=production`, `FRONTEND_ORIGIN` (the Vercel URL), `DATABASE_URL`, `SUPABASE_URL`, `QLOO_API_KEY`, `QLOO_BASE_URL`, `YOUTUBE_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, and the agent and Person-mode limits from `CLAUDE.md`;
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
3. **Run the Playwright judge path by hand against the live site.**
4. **Run the judge path once yourself on the live site** to warm the Qloo and YouTube caches.

**Check:** the live frontend shows "Backend: ok", **Try the demo** works, and the judge path passes on the live site.

---

## Frontend: Bridge screens and caregiver tools (≈ 6 h)

### Frontend 1. Bridge screens (`/profiles/:id/bridge`)
1. Add a visitor: their name, their relation, and 3 quick favourites through search.
2. Plan a Bridge session.
3. Review it. Shared picks show prompts "for the visit".
4. Play it like any session.

### Frontend 2. "Ask the agent"
- A box on the plan screen, with examples such as "fewer sad songs" and "more film songs".
- Add a mic button only if time is left over.

### Frontend 3. Swap
An "Another like this" button on draft cards.

### Frontend 4. "What we learned"
- Shown after each session.
- Also shown in the history on the profile page.

### Frontend 5. Review queue (`/profiles/:id/review`)
Hidden items, each with **Keep hidden**, **Show again** and **Never show**.

### Frontend 6. How it works page
- The agent diagram.
- The Qloo calls, in plain words.
- The table of who does what.
- Privacy.

**Prompt for Claude Code:**
```
Read CLAUDE.md and docs/API_CONTRACT.md (Phase 4). Build features/bridge (add a
visitor with name, relation and 3 favourites via /taste/search; plan with mode
"bridge"; review with prompts "for the visit"; play like any session); an "Ask the
agent" instructions box on the plan screen with examples; an "Another like this"
swap button on draft cards; a "What we learned" panel after each session and in the
profile history; the review queue at /profiles/:id/review (Keep hidden / Show again
/ Never show); and the How it works page (agent diagram, Qloo calls in plain words,
who does what, privacy). Phone layout, keyboard access, loading/empty/error states.
Run lint and build.
```

**Check:** plan, swap, and review a hidden item on a phone.

---

## Exit check (Thursday night)

Locally (backend also run once from its Docker image):
- A Bridge session for Margaret with a grandchild's favourites shows shared picks and visit prompts.
- "Ask the agent" changes a plan, and the log shows how.
- Swap works.
- "What we learned" appears after a session.
- The review queue brings a hidden item back.
- The end-to-end test passes locally.

**Then freeze.** From now on, only bug fixes.

**Then the backend owner deploys (Backend 6).** Phase 4 is done when the judge path also passes on the live site. The frontend and agent owners stay online to test it on a phone and to help if the deploy needs a fix.

## If you're behind

- **Cut first:** the Bridge screens (keep Bridge in the API).
- **Then cut:**
  - the How it works page (put the diagram in the README);
  - the end-to-end test in CI (run it by hand instead).
- **Never cut:** the review queue, because it's how hidden items come back, and **the deploy**.
- **If you're running late on Thursday,** the deploy still goes ahead on whatever is merged and working. Cut Bridge screens first.
