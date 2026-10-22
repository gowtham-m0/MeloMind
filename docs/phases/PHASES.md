# MeloMind: phases, decisions and plan

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
- **Why:** you can switch providers, the demo never breaks, and tests run without an LLM.
- **Costs:** two code paths to keep working.
- **Mitigation:** test both paths.

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
- **Mitigation:** C records the real response shapes as soon as the key arrives and fixes the parser.

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

<!-- MORE -->
