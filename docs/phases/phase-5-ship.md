# Phase 5: Ship

**Dates:** Fri 30 Oct · **Hours:** about 5 each · **Previous:** [Phase 4](phase-4-bridge-and-freeze.md)

**Goal:** submit by **11 PM IST**, with a live app that judges can use without signing up and that stays up until judging ends.

**Rules for today:**
- **If the deploy fails, fix it first. Nothing else matters until the live site works.** (Deploying was B's Phase 4 task, Thursday night.)
- Bug fixes only. No new features.
- The hard deadline is **Sat 31 Oct, 9:15 AM IST**. Treat the overnight gap as an emergency buffer, not working time.

---

## A: screenshots, video, final UI check (≈ 5 h)

1. **Screenshots** of every main screen:
   - onboarding;
   - planning with the agent log;
   - draft review;
   - the player;
   - Person mode (warm-up, shelf and player);
   - the Memory Graph (graph, timeline, node page);
   - Bridge, if it's built.
2. **A video** of the judge path, under 2 minutes.
3. **Fix UI bugs** from the final run.
4. **Test** on a phone and in a logged-out browser.

## B: security, README, keep it running (≈ 5 h)

1. **Security pass:**
   - no secrets in the git history;
   - RLS on;
   - CORS limited to the Vercel domain;
   - rate limits work;
   - Cloudflare Turnstile on anonymous sign-in, only if time allows.
2. **README:**
   - setup;
   - an architecture diagram;
   - how to test;
   - the demo login;
   - known limitations:
     - YouTube ads;
     - Qloo coverage for older regional titles;
     - no images yet.
3. **The MIT LICENSE** shows in GitHub's About section.
4. **Keep Lightsail running until 6 Nov** (it's always on, with no cold start), check the AWS Budgets alert is set, and add a Supabase keep-alive (a GitHub Action). Both run until 6 Nov.
5. **Warm the caches:** after any bug-fix redeploy, run the judge path once on the live site.
6. **Tag** `v1.0`.

## C: Devpost description and final live run (≈ 5 h)

1. **The Devpost description:**
   - the problem;
   - what it does;
   - who does what: the person, the caregiver and the agent;
   - **what makes it Qloo-powered**;
   - how the agent works;
   - the Memory Graph;
   - safety and privacy;
   - the caregiver quote;
   - how to test it;
   - what's next: images, a Markdown export for Obsidian, care homes.
2. **Testing instructions** with the demo login, following the judge path.
3. **A final full run** with live Qloo.

If Phase 4 finishes early, C starts the description on Thursday.

---

## Before you submit (all three)

- Open the live link on another device, in another browser.
- Check every link in the submission.
- Make sure the README and the Devpost description match what the app actually does.

## Exit check

- Submitted by 11 PM IST.
- Checked from a logged-out browser.
- Lightsail is running and the Supabase keep-alive is running.
