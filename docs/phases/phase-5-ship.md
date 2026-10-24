# Phase 5: Ship

**Dates:** Fri 30 Oct · **Hours:** about 5 each · **Previous:** [Phase 4](phase-4-bridge-and-freeze.md)

**Goal:** submit by **11 PM IST**, with a live app that judges can use without signing up and that stays up until judging ends.

**Rules for today:**
- **If the deploy fails, fix it first. Nothing else matters until the live site works.** (Deploying was the backend's Phase 4 task, Thursday night.)
- Bug fixes only. No new features.
- The hard deadline is **Sat 31 Oct, 9:15 AM IST**. Treat the overnight gap as an emergency buffer, not working time.

---

## Frontend: screenshots, video, final UI check (≈ 5 h)

1. **Screenshots** of every main screen, at desktop and phone width:
   - the landing page and onboarding (favourites, taste quiz, building with the live log);
   - the home feed (sidebar, hero, category tiles, rows, right rail);
   - the detail sheet with "Where to find it";
   - the journal with voice and suggestions;
   - the taste page and taste map;
   - taste match, if it's built.
2. **A video** of the judge path, under 2 minutes. Open on the feed, not on a form.
3. **Fix UI bugs** from the final run, with `/impeccable polish` on anything you touch.
4. **Test** on a phone and in a logged-out browser.

## Backend: security, README, keep it running (≈ 5 h)

1. **Security pass:**
   - no secrets in the git history;
   - RLS on;
   - CORS limited to the Vercel domain;
   - rate limits work;
   - transcription limits work and audio is never stored;
   - Cloudflare Turnstile on anonymous sign-in, only if time allows.
2. **README:**
   - setup;
   - an architecture diagram;
   - how to test;
   - the demo login;
   - known limitations:
     - platform links are searches unless Qloo gives an external ID;
     - Qloo image coverage varies, so some cards use the designed fallback;
     - music cards are artists (Qloo has no songs);
     - YouTube preview ads, if the preview is enabled.
3. **The MIT LICENSE** shows in GitHub's About section, and the design skills' licences are kept in `.claude/skills/`.
4. **Keep Lightsail running until 6 Nov** (it's always on, with no cold start), check the AWS Budgets alert is set, and add a Supabase keep-alive (a GitHub Action). Both run until 6 Nov.
5. **Warm the caches:** after any bug-fix redeploy, run the judge path once on the live site.
6. **Tag** `v1.0`.

## Agent: Devpost description and final live run (≈ 5 h)

1. **The Devpost description:**
   - the problem: taste is split across apps that only know their own catalogue;
   - what it does: one home screen for music, films, TV and books, with reasons and links to where each lives;
   - **what makes it Qloo-powered**: cross-domain insights, cross-culture picks, the taste quiz scored by Qloo, taste match with compare, tags behind the taste page;
   - how the agent works (one agent, three workflows, the log);
   - the journal: write or speak, and your taste follows your life;
   - privacy;
   - how to test it;
   - what's next: real streaming availability, dark mode, sharing a taste card, importing from Spotify.
2. **Testing instructions** with the demo login, following the judge path.
3. **A final full run** with live Qloo.

If Phase 4 finishes early, the agent owner starts the description on Thursday.

---

## Before you submit (all three)

- Open the live link on another device, in another browser.
- Check every link in the submission.
- Make sure the README and the Devpost description match what the app actually does.

## Exit check

- Submitted by 11 PM IST.
- Checked from a logged-out browser.
- Lightsail is running and the Supabase keep-alive is running.
