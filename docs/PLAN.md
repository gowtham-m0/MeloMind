# MeloMind: plan, decisions and risks

## 0. The pivot (Sat 24 Oct)

MeloMind started as a music-and-memory session tool for people living with dementia and their caregivers. On 24 Oct, after the first live run, we changed direction.

**What we saw**
- Qloo's picks were good: from One Direction and The Strokes it returned Lorde, The 1975 and Arctic Monkeys.
- The product around them wasn't. YouTube lookups came back as Shorts and ranking clips, the session-and-approval flow was heavy, and the whole experience depended on embedded video.

**What we're building instead**
- **A personal taste dashboard** across music, films, TV and books, with the feel of the YouTube, Spotify or Netflix home screen: a hero pick, rows, thumbnails and instant feedback.
- Clicking a card **opens it where it lives** (YouTube or Spotify, Netflix or Prime Video or JioHotstar via JustWatch, Google Books or Goodreads), so we no longer depend on finding a playable video.
- An **everyday journal** you write or speak, which the agent reads for mentions that shape your feed. This keeps the best idea from the Memory Graph.
- **UI/UX is the main goal.** The frontend is rebuilt from scratch with a new design system.

**What carries over:** the repo, CI, auth, profiles, favourites, the Qloo adapters and cache, `TasteService`, the agent (research step, middleware limits, fallback, agent log), feedback and learned weights, exclusions, the favourite resolver design, and the "this or that" scoring (now the onboarding taste quiz).

**What's gone:** caregivers, Person mode, session approval, the player, reactions such as "sang along", the upset review queue, Bridge, the no-images rule and the medical-safety rules that only applied to that audience.

---

## 1. Decisions and trade-offs

These are decided. Change one only if the whole team agrees, and update `CLAUDE.md` when you do.

### Product

**1. A home feed of rows, across four kinds of taste**
- **What it is:** a hero pick plus rows ("For you", "Because you liked X", "Music", "Songs", "Films", "TV", "Books", "New and notable", "Popular in <country>", "From your journal"), each a row strategy (songs come from the `add_songs` node, decision 18b).
- **Why:**
  - Everyone already knows how to use it, so judges get it in seconds.
  - Cross-domain rows ("you like this band, so try this film") are exactly what Qloo is good at and single-domain apps can't do.
  - Rows are a clean Strategy pattern: adding one changes no workflow or API.
- **Costs:** more Qloo calls per feed; rows can repeat each other.
- **Mitigation:** one research pool shared by most rows, a per-feed Qloo budget, `qloo_cache`, dedupe across rows in the guardrails.
- **Rejected:** one long mixed list (no structure, less explainable); a chat-first UI (slower, less visual).

**2. Thumbnails on every card**
- **Why:** recognition is visual. A wall of text titles doesn't feel like a product.
- **How:** Qloo's `properties.image` for artists, films and TV; Open Library covers by ISBN for books; a designed gradient tile as the fallback.
- **Costs:** Qloo image coverage is unknown for some entities; image URLs can break.
- **Mitigation:** the fallback tile always looks intentional; `onError` swaps to it.
- **Rejected:** TMDB or Spotify image APIs (more keys and terms to manage); storing images (copyright and storage).

**3. "Open where it lives" with smart search links, not a streaming-availability API**
- **Why:** it works for every country and every platform with no extra key, and JustWatch's search page already shows which service streams a title in the user's country.
- **Costs:** a search link isn't a guaranteed "it's on Netflix".
- **Mitigation:** honest labels ("Search on Netflix"); direct links when Qloo gives a trusted external ID.
- **Rejected:** TMDB watch providers (new service and key, more work this week). Possible after judging.

**4. The taste updates visibly**
- **Why:** "it learns" must be something judges can see in 10 seconds.
- **How:** like, save, open and "not interested" update learned weights; a refresh rebuilds the feed; a toast and the agent log say what changed ("More indie rock, fewer thrillers").
- **Costs:** simple heuristics, not machine learning.
- **Mitigation:** call them what they are; they're explainable and testable.

**5. The journal is the signature feature**
- **What it is:** a daily diary you write or speak. The agent finds the artists, films, shows and books you mention, you confirm them, and they become signals and a "From your journal" row. Confirmed items also appear on the taste map.
- **Why:**
  - It's personal in a way no recommendation app is.
  - It's genuinely agentic: extraction, the hint ladder, matching, and the user confirming.
  - It shows Qloo and the agent working together on real-life text.
- **Costs:** personal data; LLM calls; speech to text.
- **Mitigation:** strict privacy (text never to Qloo, Groq only, audio discarded); suggestions need confirmation; Groq Whisper uses the key we already have.
- **Rejected:** a graph database (two Postgres tables are enough); a separate speech provider.

**6. Onboarding in about a minute**
- **Why:** first impressions decide the Design score.
- **How:** name, optional country and birth year, pick favourites with image search, then a 6-round "this or that" taste quiz, then the feed builds live in front of you.
- **Costs:** the quiz needs a set to score; the first feed takes up to 25 seconds.
- **Mitigation:** the quiz set comes from popular items for the country (cached); the build screen shows the agent log as it works.

**7. Favourites can be entered as names, song titles or remembered lyrics**
- **Why:** people remember a line from a chorus rather than a title. It removes friction and shows the agent working.
- **Costs:** the AI can guess wrong; extra Qloo calls.
- **Mitigation:** the hint ladder, limited to 5 searches; the user confirms every guess; plain search-and-pick stays the main path.
- **Copyright:** a lyric is only a search hint. It's never stored or displayed.

**8. Netflix-style profiles**
- **Why:** households share devices, and the demo can show two very different tastes side by side.
- **Costs:** a profile picker screen.
- **Mitigation:** it reuses the existing profiles code.

### Agent

**9. One agent on LangGraph, built as a hybrid, with three workflows**
- **What it is:**
  - Fixed workflows where code controls the order.
  - One research step where a tool-calling agent (LangChain `create_agent`) decides its own Qloo calls.
  - The same tools power three workflows: building the feed, resolving a favourite, and linking a journal entry.
- **Why:** it's genuinely agentic where it matters (choosing Qloo calls, recovering from empty results, reading journal entries), and predictable everywhere else (rows, ranking, guardrails). It clearly meets the "built with an agent framework" rule.
- **Costs:** two layers to understand; prompts and tools need careful testing.
- **Mitigation:** middleware limits (12 Qloo calls, 8 model calls, 25 seconds); a rule-based fallback; exclusions added inside the tool; a scripted fake model in tests.
- **Rejected:** a fixed graph only (looks like a pipeline); fully agentic rows (slow and unpredictable); Deep Agents (overkill); multi-agent (more failure points).

**10. The LLM behind a port, with a template fallback**
- **Choice:** Gemini (`gemini-3.8-flash`) as the main model, Groq (`openai/gpt-oss-120b`) as the fallback. Groq Whisper for speech.
- **Changed 24 Oct:** Groq was the main model, but its free tier's 8,000 tokens a minute broke feed builds. Every pick comes from Qloo, so the model's own knowledge doesn't affect freshness; limits and reliability do.
- **Why:** you can switch providers, the demo never breaks, and tests run without an LLM.
- **Mitigation:** journal text stays on Groq (called explicitly), because a free Gemini key can use prompts for training.

**11. Simple, interpretable learning rules**
- **Why:** explainable, no training data, easy to test and show.
- **Costs:** simpler than machine learning.
- **Mitigation:** the honest framing is "configurable heuristics".

### Platform

**12. Python and FastAPI for the backend** — unchanged. The `Dockerfile` exists; restrict CORS to the Vercel domain when deploying.

**13. React, Vite and TypeScript, with a new design system**
- **Why:** the old screens were designed for older users; the new product needs a modern, premium look.
- **How:** the layout of the reference mockup (`image.png`: sidebar, search, hero banner, category tiles, rows, a right rail with mood chips, quick actions and cross-culture picks) with a light look inspired by yuzuhire.com (Chillax and Switzer, amber `#E8A838`, glass top bar). Tokens and components in `shared/ui/`. See `CLAUDE.md`, "Design system".
- **Design skills are compulsory:** `impeccable` and Emil Kowalski's skills (`emil-design-eng`, `animate`, `review-animations`, `improve-animations`, `break-ui`), committed in `.claude/skills/` so all three of us use the same ones.
- **Proposed additions (need team agreement, rule 15):** Fontshare fonts (a stylesheet link, no package); optionally `framer-motion` for card and sheet motion. Without it, use CSS transitions.

**14. One monorepo** — unchanged.

**15. Supabase (Postgres plus anonymous auth)** — unchanged. A daily keep-alive request.

**16. SQLAlchemy and Alembic** — unchanged. New tables: `feeds`, `journal_nodes`, `journal_links`. The sessions tables are dropped in a migration.

**17. A Qloo adapter with hand-written fixtures and a live mode** — unchanged. Fixtures gain image URLs that point at nothing real (the UI shows the fallback tile) and are labelled demo data.

**18. YouTube is optional**
- **Why:** quota is about 100 searches a day and search quality is mixed (Shorts, ranking clips). The feed must not depend on it.
- **How:** only the detail view's Preview button calls it, on demand, cached, with the Shorts filter.

**18b. Songs from Apple's iTunes Search API, as a lookup only** (added 25 Oct)
- **What it is:** a "Songs for you" row and song cards: the top tracks of the artists Qloo already picked for the feed, with artwork, a 30-second preview and an Apple Music link. An artist's detail view lists their top songs; a song's "More like this" is "After this song".
- **Why:** people think in songs, not artists, and Qloo has no song type. A song card plays on tap and opens straight on Apple Music, which makes music feel as concrete as films and books.
- **Keeps rule 1:** Qloo still decides what's recommended (the artist); the catalogue only looks up that artist's songs. Signals on a song count for its artist.
- **Costs:** a new external service, about 20 calls a minute, and Apple's terms (previews streamed only, shown next to the store link, credited "courtesy of iTunes").
- **Mitigation:** no key needed; an in-memory cache and a rate limiter; an 8-second deadline per feed; no catalogue, or a failure, simply means no songs row; `SONGS_ENABLED=false` turns it off. Only Qloo's artist names are sent.
- **Rejected:** Spotify (recommendations and related artists are closed to new apps, and Development Mode drops artist top tracks); ListenBrainz and Last.fm similar-track recommenders (Qloo stays the only recommender); Deezer (song search came back empty); LLM-written song lists (break rule 1).

**19. Polling for agent runs** — unchanged. Feed builds, favourite resolving and journal linking all poll `/agent-runs/{id}`.

**20. API types generated from the OpenAPI schema** — unchanged.

**21. Hosting on Vercel, AWS Lightsail and Supabase, once, on Thursday night** — unchanged.

### Process

**22. Focused testing:** the critical rules plus one end-to-end test.

**23. Claude Code writes most of the code**, with `CLAUDE.md`, contracts first, a human reading every line, and small PRs.

---

## 2. Hard questions we checked

| Question | Answer |
|---|---|
| Isn't this just Netflix? | Netflix only knows Netflix. MeloMind spans music, films, TV and books and links across them ("you love this band, so try this film"), which is what Qloo's cross-domain graph is for. And it explains every pick. |
| Is the agent really agentic, or a pipeline with an LLM? | The research step chooses its own Qloo calls, the hint ladder recovers from empty results, and journal linking is the agent's own reading of your words. The log shows each decision. |
| Do the links actually take you to the thing? | Music opens the artist's top songs on YouTube or Spotify. Films and TV open JustWatch for your country, which lists where it streams, plus Netflix and Prime search. Books open by ISBN when we have it. Labels say "Search on" unless the link is direct. |
| What if Qloo has no image? | A designed gradient tile with the type's colour and icon. It's part of the design, not a broken image. |
| What if Qloo has nothing for someone? | The quiz picks, country and popularity carry the first feed, and the fallback relaxes its queries twice. The log says what happened. |
| Isn't a journal a privacy risk? | Entries are private to the profile, never sent to Qloo, seen by the LLM only while suggesting links (Groq only), and voice is never stored. Entries can be deleted. |
| Can a judge see everything in 5 minutes, without real data? | Yes. The demo profiles come with favourites, likes and journal entries with confirmed links (see "The judge path"). |
| What if we run out of time? | The build order means the unfinished part is the least important one, and the cut lines decide what goes. |

---

## 3. Open decisions

1. **Team agreement on the pivot** (all three, Sat 24 Oct).
2. **`framer-motion`:** yes or no (frontend owner proposes).
3. **Taste map library:** react-force-graph or Cytoscape.js (Phase 3, first hour).
4. **Name:** keep MeloMind (decided 24 Oct).

---

## 4. Roles and ownership

| Owner | Area | Owns |
|---|---|---|
| **Frontend** | Frontend and experience | `frontend/**`: the design system, onboarding, the feed, the detail view, the taste page, the journal and the taste map; accessibility; screenshots and video |
| **Backend** | Backend platform and data | `backend/app/api/**`, `infrastructure/persistence/**`, `alembic/`; the application services except `TasteService` (profiles, feed, feedback, quiz, journal, taste profile); `domain/links.py`; auth, CI, the `Dockerfile`, the Thursday-night deploy, the end-to-end test, the README |
| **Agent** | Agent and integrations | `application/agent/**`, `application/rows/**`, `TasteService`, `infrastructure/{qloo,media,llm}/**`; `docs/AGENT.md`, `docs/QLOO_NOTES.md`; demo fixtures; the Devpost description |

**Shared files** (one person leads, one reviews):

| File | Leads | Reviews |
|---|---|---|
| `domain/models.py`, `domain/feed.py` | Backend | Agent |
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
- Reviewers check the layer rule, no secrets, no real Qloo data, tests exist, and the contract is updated.
- For screens, the reviewer also opens the preview at phone and desktop width and compares it with the design system.

**Contracts**
- When a contract changes, the owner updates `API_CONTRACT.md` first, tells the team, and then builds.
- The frontend can build against a contract before its route exists, by mocking responses with the generated types.

---

## 6. The judge path

This is what a judge does in about 5 minutes. The demo data, the end-to-end test, the video and the testing instructions all follow it.

1. Open the app and tap **Try the demo**. Pick the profile **Aanya** (indie and alt rock, Bangalore).
2. The **feed** opens instantly: a hero pick and rows with thumbnails. Hover a card and read why it's there.
3. Open a card's **detail view**: why you're seeing it, where to find it, more like this. Tap **Search on Netflix** or **Listen on YouTube**; it opens in a new tab.
4. **Like** two items and mark one **Not interested**. Tap **Refresh**: the rows change, the dismissed item is gone, and the toast and agent log say what changed.
5. Open the **journal**. Speak or type "Rewatched Interstellar with my brother, then had Glass Animals on repeat." Confirm the suggested links.
6. Back on the feed, **From your journal** has appeared.
7. Open the **taste page**: your taste in a sentence, top tags, and the taste map with the new journal links.
8. (Optional) **Start fresh**: make a new profile, add 3 favourites, take the taste quiz, and watch the first feed build live.

The second demo profile, **Leo** (classic films and jazz, US), shows how different a feed can be.

---

## 7. Phases

Each phase has its own file in `docs/phases/`, with the contract, every person's tasks, Claude Code prompts and checks.

**Build order:** the feed and the new frontend, then the journal and taste page, then polish. Don't start a phase's features until the previous phase's exit check passes.

| Phase | Dates | Goal | Done when |
|---|---|---|---|
| [0. Kickoff and setup](phases/phase-0-setup.md) | Fri 23 Oct | Repo, folders, boilerplate, `Dockerfile` | ✓ Done |
| [1. Foundations](phases/phase-1-foundations.md) | Sat 24 Oct | Profiles, favourites, demo login, Qloo adapter | ✓ Done |
| [2. Feed and the new frontend](phases/phase-2-core-loop.md) | Sat 24 – Mon 26 Oct | Backend refactor to the feed; new design system; onboarding with the taste quiz; dashboard; detail view; feedback | Locally, liking and dismissing then refreshing changes the feed, and the log explains it |
| [3. Journal and taste page](phases/phase-3-memory-graph.md) | Tue 27 – Wed 28 Oct | Write or speak entries, link suggestions, "From your journal", taste page and taste map, favourite resolver | Locally, a spoken entry's confirmed links show in the feed and on the taste map |
| [4. Polish and freeze](phases/phase-4-bridge-and-freeze.md) | Thu 29 Oct | Ask the agent, Taste match, motion and states polish, end-to-end test, then the one and only deploy | **Feature freeze on Thursday night**, then the live site is deployed and the judge path runs on it |
| [5. Ship](phases/phase-5-ship.md) | Fri 30 Oct | Submission | Submitted by **11 PM IST**, and checked from a logged-out browser |

The hard deadline is **Sat 31 Oct, 9:15 AM IST**. Treat the overnight gap as an emergency buffer, not as working time.

---

## 8. Hand-offs

| Who needs | What | From | By |
|---|---|---|---|
| All | Pivot agreed, new docs read | All | Sat 24, evening |
| Frontend, Agent | Phase 2 contract (feed, items, feedback, quiz) | Backend | Sat 24, night |
| Frontend | Design system tokens and components in `shared/ui/` | Frontend | Sun 25, noon |
| Backend | `TasteGraph` returns images and external IDs | Agent | Sun 25, noon |
| Frontend | Stub feed in the real shape (fixtures) | Agent | Sun 25, noon |
| Backend | `build_feed` workflow and row strategies merged | Agent | Mon 26, 8 PM |
| All | Feed loop working locally | All | **Mon night** |
| Frontend, Agent | Phase 3 contract and journal repositories | Backend | Tue 27, start of the evening |
| Backend | `link_journal` and `resolve_favourite` callable | Agent | Tue night |
| Frontend | Journal and taste routes live | Backend | Wed 8 PM |
| All | Feature freeze | All | **Thu night** |
| All | Live site deployed | Backend | Thu night |

---

## 9. Risks

| Risk | Level | Mitigation | Owner |
|---|---|---|---|
| The pivot costs a day | High | Reuse the backend; rebuild only the frontend; cut lines below | All |
| Qloo images are missing for many items | Medium | Check coverage first thing in Phase 2; designed fallback tiles; Open Library for books | Agent |
| Feeds feel repetitive or random | Medium | One research pool, dedupe across rows, reasons on every card, "Because you liked X" rows | Agent |
| Feed builds are slow (25 s) | Medium | Saved snapshot opens instantly; rebuilds in the background; `qloo_cache` | Agent |
| Search links feel unreliable | Low–Medium | Honest labels, JustWatch per country, direct links from external IDs | Backend |
| The LLM is slow, wrong or down | Medium | Structured output, timeouts, the template fallback | Agent |
| Speech to text fails or is slow | Medium | Typing always works; show the transcript for editing; Groq only | Agent |
| Journal entries hold personal data | Medium | Privacy rules (`CLAUDE.md`, rule 11), deleted with the profile | Backend |
| The new design isn't finished in time | High | Design system first (Sunday noon), then screens; cut dark mode and motion first | Frontend |
| The app is asleep or paused during judging | High | Lightsail always on, a Supabase ping, a check on 2 Nov | Backend |
| The first deploy fails close to the deadline | High | Dockerfile from Phase 0, deploy Thursday night with Friday as the buffer | Backend |
| Three people's AI-written code doesn't fit together | High | `CLAUDE.md`, contracts first, a human reviews every PR | All |

---

## 10. Cut lines

| If behind on | Cut first | Then cut |
|---|---|---|
| Monday night (no feed loop) | The `throwback` and `popular_<country>` rows; "More like this" | The taste quiz (favourites only) |
| Monday night (research agent unreliable) | Make the rule-based pool the default, with the agent behind a flag | Make journal linking the agentic showcase |
| Wednesday night (journal unfinished) | The taste map (keep the list); voice (keep typing) | The favourite resolver ("type a line you remember") |
| Thursday night | Taste match; Ask the agent; dark mode | The end-to-end test in CI (run it by hand) |
| Friday | The video (screenshots are enough) | Polish |

**Never cut:**
- demo login;
- thumbnails (or the designed fallback) on every card;
- platform links on every item;
- the guarantee that "not interested" items never return;
- a reason on every pick, and the agent log;
- user confirmation of journal links;
- deployment (one working live site), and keeping the app awake through judging.

---

## 11. After submission (31 Oct to 6 Nov)

- **Don't change the submitted code.** Only keep the infrastructure running.
- Check the live site on **2 Nov**, the day judging starts, and again mid-week.
- Keep Lightsail running and the Supabase ping going until **6 Nov, 10:15 AM IST**.
- Watch Devpost and email for any questions from judges.
- **After judging:** real streaming availability (TMDB watch providers), dark mode, sharing a taste card, Spotify import.
