# MeloMind: plan, decisions and risks

## 1. Decisions and trade-offs

These are decided. Change one only if the whole team agrees, and update `CLAUDE.md` when you do.

### Product

**1. The caregiver runs MeloMind, the person chooses by tapping, and the AI never talks to the person**
- **Why:**
  - It's safe, and judges will trust it.
  - The person keeps real choice without having to talk to a machine.
  - The caregiver controls everything the person sees.
- **Costs:** less "wow" than a talking companion.
- **Mitigation:** Person mode, the Memory Graph and the Bridge session provide the emotional moments instead.
- **Rejected:** a chat or voice companion for the person, because:
  - it could confuse or distress them;
  - speech recognition struggles with impaired speech;
  - it raises consent questions we can't answer in 9 days.

**2. Person mode: big cards and taps, not conversation**
- **Why:**
  - It answers "how does the person choose?" without any AI conversation.
  - Two big cards at a time keep the choice simple, with the caregiver beside them.
  - Each tap is a gentle learning signal.
- **Costs:**
  - A second interface to build and test.
  - Taps are noisy, because a person may tap at random.
  - Without pictures, the cards rely on reading (see decision 7).
- **Mitigation:**
  - Only caregiver-approved, playable items appear.
  - Tap weights are small and count once per item per day, and a skip never hides anything.
  - A large Stop button, no time limits, no autoplay, and a caregiver unlock to leave.
- **Rejected:**
  - autoplay radio, which removes the person's choice;
  - a search box or menus, which are too hard to use.

**3. Cold start from Qloo, with a warm-up that's just another session mode**
- **Why:**
  - Qloo needs no history, so a birth year alone gives a first session. That's a strong Qloo story for judges.
  - The `warmup` mode reuses approval, guardrails and exclusions. It also proves that modes can be added without touching the workflows.
  - Every optional question has "Not sure, skip", so onboarding takes about a minute.
- **Costs:**
  - The first picks are generic when the family gives nothing specific.
  - The warm-up costs up to 6 extra Qloo calls.
  - Scoring a set with `filter.results.entities` is unverified.
- **Mitigation:**
  - A high popularity floor, so the first picks are the big hits of their youth.
  - Cache Qloo responses.
  - If set scoring doesn't work, pick the same type and the closest year.

**4. The Memory Graph is the signature feature**
- **What it is:** linked notes about the person's life (people, places, songs, films and decades), with backlinks and graph, timeline and list views. It works like Obsidian, but inside MeloMind.
- **Why:**
  - Nothing else in this space connects one person's memories to a taste graph.
  - It's visual: judges watch the graph grow as the agent suggests links.
  - It shows Qloo and the agent working together. Song and film nodes are Qloo entities, and "because of" links come from Qloo.
  - It makes sessions more personal over time.
  - It gives the family something lasting.
- **Costs:**
  - The biggest new feature.
  - Graph views can look empty or messy.
  - It holds personal data.
  - More LLM calls.
- **Mitigation:**
  - Seeded demo memories, a 30-node cap, grouping by decade, and a list view that always works.
  - The caregiver confirms every suggested link.
  - Strict privacy rules (`CLAUDE.md`, rule 14).
  - Built after the core loop, so nothing in the core depends on it.
- **Rejected:**
  - **Connecting to real Obsidian.** Its Local REST API is a desktop-only community plugin on localhost, so judges couldn't use it. A Markdown export that opens in Obsidian is possible later.
  - **A graph database such as Neo4j.** It's another service to run, and overkill for a few hundred nodes per profile. Two Postgres tables are enough.
  - **Plain notes without links.** They'd give the agent nothing to use and judges nothing to see.

**5. The Bridge session is the second showcase, built last**
- **Why:** it's emotional, it shows off Qloo's compare endpoint, and it's smaller than a group mode.
- **Costs:** it may be cut, and its business story is weaker than care homes.
- **Mitigation:**
  - Start it only after the Memory Graph's exit check passes.
  - The pitch works without it.
  - Mention care homes under "What's next".

**6. A bigger scope: the core loop, the Memory Graph and Bridge**
- **Why:** Claude Code writes most of the code, so the team chose the full vision.
- **Costs:**
  - About 47 hours each instead of 39.
  - Claude Code writes quickly, but a person still reviews every line, tests on a phone and fixes integration bugs. That's where the time goes.
  - With day jobs, the feature freeze moves to Thursday night, and Friday is the only shipping day.
- **Mitigation:**
  - The build order, so whatever is unfinished is the least important part.
  - The cut lines.
  - Ask at kickoff whether anyone can take Thursday or Friday off.

**7. No images for now**
- **Why:** it keeps the scope down. Cards with a title, a type icon, the year and a decade colour are clear enough to build and test the product.
- **Costs:** pictures are easier to recognise than written titles for many people, especially as reading gets harder, so Person mode is weaker without them.
- **Mitigation:** design the card with room for an image, so adding one later is a small change.

**8. Favourites can be entered as names, song titles or remembered lyrics**
- **Why:** families often remember a line from a chorus rather than a title. This removes friction and shows the agent working.
- **Costs:**
  - The AI can confidently guess wrong, especially for obscure or regional songs.
  - Extra Qloo calls.
- **Mitigation:**
  - The hint ladder, limited to 5 searches per favourite.
  - The caregiver confirms every guess.
  - Plain search-and-pick stays the main path.
- **Copyright:** a lyric is only a search hint. It's never stored or displayed.

**9. Voice is optional, for the caregiver only, and last priority**
- **Why:** it adds no Qloo depth and can fail during judging. The person never uses voice (decision 1).
- **Costs:** looks less flashy.
- **Mitigation:** add a mic button to "Ask the agent" only if time is left over.

### Agent

**10. One agent on LangGraph, built as a hybrid, with three workflows**
- **What it is:**
  - Fixed workflows where code controls the order.
  - One research step where a tool-calling agent (LangChain `create_agent`) decides its own Qloo calls.
  - The same tools power three workflows: planning a session, resolving a favourite, and linking a memory note.
- **Why:**
  - It's genuinely agentic where it matters. The agent chooses its Qloo calls, recovers from empty results and suggests links, and the log shows its reasoning.
  - Everything else stays predictable: ranking, media lookups and guardrails.
  - It clearly meets the "built with an agent framework" rule.
- **Costs:**
  - Two layers to understand.
  - The prompts and tools need careful testing.
  - More LLM calls than a fixed pipeline.
- **Mitigation:**
  - Hard limits through middleware: 12 Qloo calls, 8 model calls, 25 seconds.
  - A rule-based fallback whenever the agent fails or hits a limit.
  - Exclusions are added inside the tool, so the agent can't skip them.
  - Tests use a scripted fake model.
- **Rejected:**
  - **A fixed graph only:** it looks like a pipeline and can't improvise.
  - **Fully agentic:** 30–60-second sessions, a burnt YouTube quota and an unpredictable demo.
  - **Deep Agents:** built for long research and coding jobs, so overkill for a 20-second task.
  - **Multi-agent:** more failure points, and slower.

**11. The LLM behind a port, with a template fallback**
- **Choice:** Groq (`openai/gpt-oss-120b`) as the main model, for speed inside the 25-second budget, with Gemini (`gemini-3.8-flash`) as the fallback when Groq fails or times out. A factory builds either one.
- **Why:** you can switch providers, the demo never breaks, and tests run without an LLM.
- **Costs:** two code paths to keep working, and a second provider's key.
- **Mitigation:** test both paths. Memory notes stay on Groq, because a free Gemini key can use prompts for training.

**12. Simple, interpretable learning rules from caregiver reactions and the person's taps**
- **Why:** they're explainable, need no training data, and are easy to test and show judges.
- **Costs:** simpler than machine learning, and taps are noisy.
- **Mitigation:**
  - The honest framing is "configurable heuristics".
  - Caregiver reactions outweigh taps, and only the caregiver can hide or reject an item.

### Platform

**13. Python and FastAPI for the backend**
- **Why:** the team knows Python, LangGraph is native to it, Pydantic gives typed schemas, and the API docs are generated automatically.
- **Costs:** one deployment at the end (Vercel and Lightsail), with CORS setup, so a deploy problem shows up late.
- **Mitigation:**
  - The `Dockerfile` exists from Phase 0, and the backend is tested in Docker locally in every phase.
  - Restrict CORS to the Vercel domain when deploying.
- **Rejected:** Next.js full-stack, because the team is less fluent in it and LangGraph's JavaScript version lags the Python one.

**14. React, Vite and TypeScript for the frontend**
- **Why:** a large ecosystem, accessible components quickly from shadcn/ui, and it deploys as static files.
- **Costs:** if your frontend person knows Angular better, React is slower for them.
- **Mitigation:** decide at kickoff, because the framework matters less than fluency.
- **Rejected:** Next.js, since no server rendering is needed.

**15. One monorepo**
- **Why:** one public repo to submit, shared docs and `CLAUDE.md`, and one CI.
- **Costs:** two deploy roots.
- **Mitigation:** build the Docker image from `backend/` for Lightsail, and set Vercel's root folder to `frontend/`.

**16. Supabase (Postgres plus anonymous auth)**
- **Why:** a managed database, free, and anonymous sign-in gives each judge their own data with no sign-up.
- **Costs:**
  - The free plan pauses after 7 days of low activity.
  - Verifying logins takes some setup.
- **Mitigation:**
  - A daily keep-alive request.
  - Verify tokens against the JWKS using PyJWT.
- **Rejected:**
  - SQLite inside the container, because data is lost on redeploy;
  - no auth at all, because judges would see each other's data;
  - Firebase, because the team knows it less well.

**17. SQLAlchemy and Alembic**
- **Why:** standard, testable, and migrations live with the backend code.
- **Costs:** some boilerplate.
- **Mitigation:** keep models simple, and keep in-memory repositories for tests.
- **Rejected:** calling the Supabase client from the backend, which ties the code to one vendor and is harder to test.

**18. A Qloo adapter with hand-written fixtures and a live mode**
- **Why:** you can build before the key arrives, the demo still works if Qloo has problems, and tests are deterministic.
- **Costs:** the fixtures may not match real responses exactly.
- **Mitigation:** the agent owner records the real response shapes as soon as the key arrives and fixes the parser.

**19. YouTube for media**
- **Why:** it has the widest catalogue, including old and Indian music and film clips. It also embeds, and it's free.
- **Costs:**
  - About 100 searches a day.
  - Some videos can't be embedded.
  - Ads may play in embedded videos.
- **Mitigation:**
  - Cache every lookup.
  - Check `embeddable` before using a video.
  - Pre-warm the demo profiles.
  - List ads under known limitations.
- **Rejected:**
  - Spotify, which hasn't given new apps 30-second previews since Nov 2024;
  - Apple Music, which needs a paid developer account and a subscription.

**20. Polling for agent runs**
- **Why:** simple, and it works through any proxy. Planning, resolving a favourite and linking a note all poll the same `/agent-runs/{id}` route.
- **Costs:** updates arrive about a second late.
- **Mitigation:** poll every second while a run is going. Server-sent events (SSE) can come later if there's time.

**21. API types generated from the OpenAPI schema**
- **Why:** the frontend and backend can't drift apart silently.
- **Costs:** one more script.
- **Mitigation:** run `npm run gen:api` after every API change.

**22. Hosting on Vercel, AWS Lightsail and Supabase, once, on Thursday night**
- **Why:**
  - Lightsail's container service is always on, so there's no cold start while judges try the app. It costs about $7/month.
  - Vercel serves the static frontend, and Supabase holds the database and auth.
  - Hosting happens once, on Thursday night after the feature freeze. Until then everything runs on localhost, with the backend also tested in Docker, and Supabase used from localhost.
- **Costs:**
  - About $7/month on a personal AWS account, until 6 Nov.
  - Supabase's free plan can pause.
  - AWS setup (IAM, ports, env vars) is new work on the deadline path.
- **Mitigation:**
  - An IAM user limited to Lightsail, and an AWS Budgets alert (for example $10).
  - A daily Supabase ping.
  - Friday is the buffer for a failed deploy.

### Process

**23. Focused testing: the critical rules plus one end-to-end test**
- **Why:** it protects what judges will actually try, within the time available.
- **Costs:** lower overall coverage.
- **Mitigation:** the must-have tests listed in `CLAUDE.md`.

**24. Claude Code writes most of the code**
- **Why:** much faster.
- **Costs:** three people's AI sessions can produce code that doesn't fit together.
- **Mitigation:**
  - the rules in `CLAUDE.md`;
  - API contracts agreed first;
  - a human reads every line of every PR;
  - small PRs.

---

## 2. Hard questions we checked

Before building, we put the plan through the questions a sceptical judge or teammate would ask.

| Question | Answer |
|---|---|
| Isn't Person mode the AI talking to the person? | No. Person mode shows only the titles, type icons and years of items the caregiver approved. It never shows prompts, reasons or any other AI-written text. |
| What if the person taps at random? | Taps carry small weights and count once per item per day, and a skip never hides anything. Caregiver reactions outweigh them, and "What we learned" shows what changed. |
| What if the person taps something upsetting? | Only approved items appear, and Stop is always on screen. The caregiver's long-press button hides the item at once and sends it to the review queue. |
| What if Qloo has nothing for this person? | The cold-start tiers fall back to era, region and the age signal, and the fallback relaxes its queries twice. The log says what happened. |
| Is the agent really agentic, or a pipeline with an LLM? | The research step chooses its own Qloo calls, the hint ladder recovers from empty results, and the link suggestions are its own reading of a note. The log shows each decision. |
| Is the Memory Graph just a notes app? | No. Song, artist, film and book nodes are Qloo entities the agent resolved, "because of" links come from Qloo, and confirmed nodes can become Qloo signals. |
| Could a personal prompt hurt someone, for example by mentioning a spouse who has died? | Each node has a "Use in prompts" switch, and the caregiver sees, and can edit, every prompt before approving a session. |
| Isn't storing memories a privacy risk? | Notes are private to the profile and never sent to Qloo. The LLM sees one only while suggesting its links. There are no medical fields, and notes are deleted with the profile. |
| Can a judge see everything in 5 minutes, without real data? | Yes. The demo profiles come with favourites, memories with confirmed links, and a warm-up set ready to approve (see "The judge path"). |
| What if we run out of time? | The build order means the unfinished part is the least important one, and the cut lines decide what goes. |
| Will the name cause trouble? | Possibly, because "Melomind" is an existing EEG headset. Decide at kickoff. |

---

## 3. Open decisions for the kickoff (Phase 0)

1. **Roles:** who owns the frontend, the backend and the agent. The person who knows LangGraph best should own the agent.
2. **Frontend framework:** React, unless your frontend person is much faster in Angular.
3. **LLM provider:** decided: Groq as the main model, Gemini as the fallback (see decision 11). Use personal accounts with a spending cap, never work accounts.
4. **Name:** "Melomind" is already the name of myBrain Technologies' EEG relaxation headset, which uses music, so it's close to your space. Either keep it and accept some confusion and trademark risk, or pick another name now, before anything is published.
5. **Time off:** the plan has about 2 hours of slack per person. If anyone can take Thu 29 or Fri 30 Oct off, say so now. It decides how likely Bridge is to make it.
6. **Daily check-in time:** a fixed 10 minutes.
7. **Qloo key:** requested; the agent owner tracks it.

---

## 4. Roles and ownership

| Owner | Area | Owns |
|---|---|---|
| **Frontend** | Frontend and experience | `frontend/**`, including Person mode and the Memory Graph views; design and accessibility; caregiver conversations; screenshots and video |
| **Backend** | Backend platform and data | `backend/app/api/**`, `infrastructure/persistence/**`, `alembic/`; the application services except `TasteService` (profiles, sessions, feedback, shelf, warm-up, memory); auth, CI, the `Dockerfile`, the Thursday-night deploy, the end-to-end test, the README |
| **Agent** | Agent and integrations | `application/agent/**`, `application/modes/**`, `TasteService`, `infrastructure/{qloo,media,llm}/**`; `docs/AGENT.md`, `docs/QLOO_NOTES.md`; demo fixtures; the Devpost description |

**Shared files** (one person leads, one reviews):

| File | Leads | Reviews |
|---|---|---|
| `domain/models.py` | Backend | Agent |
| `domain/policies.py` (learning rules) | Backend | Agent |
| `application/ports.py` | Agent | Backend |
| `docs/API_CONTRACT.md` | Backend | Frontend |
| `api/deps.py` | Backend | Agent |

---

## 5. Working with Claude Code as a team

**Starting a session**
- Start every session with: *"Read CLAUDE.md and docs/phases/phase-N-….md, task Backend 3. Plan first and list the files you'll touch."*
- Use plan mode for any task that touches more than 3 files. Approve the plan before Claude writes code.

**Scope**
- One task per session, and one branch per task.
- Commit small and often.
- Ask Claude to **run the tests and lint** and to show you the output before you commit.

**Reviewing**
- **A human reads every line before merging.**
- Reviewers check:
  - the layer rule;
  - no secrets;
  - no real Qloo data;
  - tests exist;
  - the contract is updated.
- For screens, the reviewer also opens the preview at phone width.

**Contracts**
- When a contract changes, the owner updates `API_CONTRACT.md` first, tells the team, and then builds.
- The frontend can build against a contract before its route exists, by mocking responses with the generated types.

**Skills**
- If you add Claude Code skills (for UI polish, planning or reviews), read them first. Then commit them to the repo's `.claude/skills/` so all three of you use the same ones.

---

## 6. The judge path

This is what a judge does in about 5 minutes. The demo data, the end-to-end test, the video and the testing instructions all follow it.

1. Open the app and tap **Try the demo**.
2. Open Margaret's profile. Her favourites and memories are already there.
3. **Plan today's session** and watch the agent log.
4. Review the draft and **approve** it.
5. Play an item, mark it **sang along**, and **reject** another.
6. Open **Person mode**. Approve the warm-up set, do the warm-up, play from the shelf and tap ♥.
7. Add a **memory note**, confirm the agent's suggested links, and find the note in the graph.
8. **Plan again.** The picks change, a prompt uses the memory, and the log explains why.
9. If it's built, plan a **Bridge** visit with a grandchild's 3 favourites.

Lakshmi (born 1950, Chennai) is the second sample profile. Keep her only if Qloo's coverage of older Indian titles is good enough (the agent owner checks this in Phase 1).

---

## 7. Phases

Each phase has its own file in `docs/phases/`, with the contract, every person's tasks, Claude Code prompts and checks.

**Build order:** the core loop, then the Memory Graph, then Bridge. Don't start a phase's features until the previous phase's exit check passes.

| Phase | Dates | Goal | Done when |
|---|---|---|---|
| [0. Kickoff and setup](phases/phase-0-setup.md) | Fri 23 Oct | Open decisions, then the repo, folders, boilerplate and a `Dockerfile`. **No business logic** | Locally, the frontend shows "Backend: ok" from the backend (also running in Docker), and CI is green |
| [1. Foundations](phases/phase-1-foundations.md) | Sat 24 Oct | Onboarding with cold-start inputs, profiles, favourites, demo login, Qloo adapter | Locally, a profile created with only a name and birth year saves, and 3 favourites added by search survive a refresh |
| [2. Core loop](phases/phase-2-core-loop.md) | Sun 25 – Mon 26 Oct | Agent, sessions, caregiver review and player, Person mode, learning | The full loop and Person mode work locally, and the second plan changes because of them |
| [3. Memory Graph](phases/phase-3-memory-graph.md) | Tue 27 – Wed 28 Oct | Notes, suggested links, backlinks, views, personal prompts, favourite resolver | Locally, a note's confirmed links show in the graph, and the next session's prompts use them |
| [4. Bridge and freeze](phases/phase-4-bridge-and-freeze.md) | Thu 29 Oct | Bridge, swap, Ask the agent, review queue, end-to-end test, then the one and only deploy | **Feature freeze on Thursday night**, then the live site is deployed and the judge path runs on it |
| [5. Ship](phases/phase-5-ship.md) | Fri 30 Oct | Submission | Submitted by **11 PM IST**, and checked from a logged-out browser |

**Hours per person:**
- Phase 0: about 4.5
- Phase 1: about 7
- Phase 2: about 15
- Phase 3: about 10
- Phase 4: about 6
- Phase 5: about 5
- **Total: about 47**

About 49 hours are available each: a long Friday evening, two full weekend days and five weekday evenings. That leaves about 2 hours of slack, so use the cut lines rather than late nights.

The hard deadline is **Sat 31 Oct, 9:15 AM IST**. Treat the overnight gap as an emergency buffer, not as working time.

---

## 8. Hand-offs

| Who needs | What | From | By |
|---|---|---|---|
| Frontend, Agent | The repo exists | Backend | Fri 23, first hour |
| Frontend | Phase 1 contract | Backend | Sat 10 AM |
| Backend | Domain models agreed | Agent reviews | Sat 11 AM |
| Backend | `TasteService.search`, for `/taste/search` and the demo seed | Agent | Sat 4 PM |
| Frontend, Backend | Phase 2 contract | Backend | Sun 10 AM |
| Frontend, Backend | Stub planner in the real shape | Agent | Sun 11 AM |
| Backend | `TasteService.score`, for the warm-up | Agent | Sun evening |
| Agent | `media_cache` and `agent_runs` repositories (in-memory until then) | Backend | Sun evening |
| Frontend | Phase 2 routes running on localhost (the planner may still be the stub) | Backend | Sun night |
| Backend | Real planner merged | Agent | Mon 8 PM |
| All | Full loop and Person mode working locally | All | **Mon night** |
| Frontend, Agent | Phase 3 contract and memory repositories | Backend | Tue, start of the evening |
| Backend | `resolve_favourite` and `link_memory` callable | Agent | Tue night |
| Frontend | Memory routes live | Backend | Wed 8 PM |
| Agent | Caregiver quote | Frontend | Wed night |
| Frontend | Bridge, swap, instructions, "learned" and review-queue routes | Backend, Agent | Thu 8 PM |
| All | Feature freeze | All | **Thu night** |
| All | Live site deployed | Backend | Thu night |

---

## 9. Risks

| Risk | Level | Mitigation | Owner |
|---|---|---|---|
| The Qloo key arrives late | Medium | Fixtures carry Phases 0–2; ask in #api-help | Agent |
| Qloo has little data for older or Indian titles | Medium | Coverage check in Phase 1, the hint ladder and fallbacks; lead the demo with Margaret | Agent |
| A Qloo parameter we rely on doesn't work (`filter.results.entities`, compare, the age signal) | Medium | The "To verify" list in Phase 1, with a fallback for each | Agent |
| The LLM is slow, wrong or down | Medium | Structured output, a 15-second timeout, the template fallback | Agent |
| The research agent loops, wanders or is slow | Medium | Middleware limits, a 25-second timeout, the rule-based fallback | Agent |
| The AI misidentifies a song or suggests a wrong link | Medium | The caregiver confirms every guess and link; rejected links are never suggested again | Agent |
| Random taps teach the wrong thing | Low–Medium | Small weights, once per item per day, skips never hide; caregiver reactions outweigh taps | Backend |
| Person mode confuses or upsets someone in real use | Medium | Only approved items, two choices at most, no time limits, Stop always visible, a caregiver present, and the caregiver button hides an item at once | Frontend |
| A personal prompt mentions someone painful | Medium | The "Use in prompts" switch; the caregiver sees and can edit every prompt | Agent |
| Memory notes hold sensitive personal data | Medium | The privacy rules (`CLAUDE.md`, rule 14), no medical fields, deleted with the profile | Backend |
| The Memory Graph looks empty or messy | Medium | Seeded memories, the 30-node cap, decade grouping, the list view | Frontend |
| YouTube quota, non-embeddable videos or ads | Medium | Cache, the embeddable check, warm caches, ads listed as a known limitation | Agent |
| The app is asleep or paused during judging | High | Lightsail always on, a Supabase ping, a check on 2 Nov | Backend |
| The first deploy fails close to the deadline | High | Dockerfile from Phase 0, test in Docker locally every phase, deploy Thursday night with Friday as the buffer | Backend |
| Three people's AI-written code doesn't fit together | High | `CLAUDE.md`, contracts first, a human reviews every PR | All |
| Merge conflicts in shared files | Medium | The ownership table; shared files change only through a PR from their lead | All |
| Scope: three big features in 8 days, alongside day jobs | High | The build order, the cut lines, a freeze on Thursday night, and asking about time off | All |
| Name confusion with the Melomind headset | Low–Medium | Decide at kickoff | All |

---

## 10. Cut lines

| If behind on | Cut first | Then cut |
|---|---|---|
| Monday night (no full loop) | The warm-up (keep the shelf) | Bridge entirely; Phase 3 shrinks to notes, backlinks and the list view |
| Monday night (research agent unreliable) | Make the rule-based plan the default, with the agent behind a flag | Make the favourite resolver and link suggestions the agentic showcase |
| Wednesday night (Memory Graph unfinished) | The graph view (keep the list, the timeline and backlinks) | Bridge entirely; Thursday goes to finishing the Memory Graph |
| Thursday night | The Bridge screens (keep the API), the How it works page | The end-to-end test in CI (run it by hand) |
| Friday | The video (screenshots are enough) | Polish |

**Never cut:**
- demo login;
- caregiver approval, and Person mode showing only approved items;
- the guarantee that excluded items never return;
- an always-visible Stop;
- the agent log;
- caregiver confirmation of Memory Graph links;
- deployment (one working live site), and keeping the app awake through judging.

---

## 11. After submission (31 Oct to 6 Nov)

- **Don't change the submitted code.** Only keep the infrastructure running.
- Check the live site on **2 Nov**, the day judging starts, and again mid-week.
- Keep Lightsail running and the Supabase ping going until **6 Nov, 10:15 AM IST**.
- Watch Devpost and email for any questions from judges.
- **After judging:** images, the Markdown export for Obsidian, and voice for the caregiver.
