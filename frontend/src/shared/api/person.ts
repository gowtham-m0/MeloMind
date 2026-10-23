import { apiRequest } from "./client";
import type { components } from "./schema";
import type { FeedbackResult, Reaction } from "./sessions";

type Schemas = components["schemas"];

/** A Person-mode card. It never has a reason or a prompt. */
export type ShelfItem = Schemas["ShelfItemOut"];
/** The next two warm-up cards, or `done`. */
export type WarmupStep = Schemas["WarmupNextOut"];
/** chose, loved, replayed or skipped. */
export type PersonSignal = Schemas["PersonSignal"];

const PROFILES = "/api/v1/profiles";

/** GET /profiles/{id}/shelf: approved, playable cards only. */
export function getShelf(profileId: string): Promise<ShelfItem[]> {
  return apiRequest<ShelfItem[]>("GET", `${PROFILES}/${profileId}/shelf`);
}

/** POST /profiles/{id}/warmup/next: records the choice and returns the next pair. */
export function nextWarmupPair(
  profileId: string,
  chosenRef: string | null,
  shownRefs: string[],
): Promise<WarmupStep> {
  return apiRequest<WarmupStep>("POST", `${PROFILES}/${profileId}/warmup/next`, {
    chosen_ref: chosenRef,
    shown_refs: shownRefs,
  });
}

/** POST /profiles/{id}/person-signals: a tap in Person mode. */
export function sendPersonSignal(
  profileId: string,
  itemRef: string,
  signal: PersonSignal,
  playedS?: number,
): Promise<FeedbackResult> {
  return apiRequest<FeedbackResult>("POST", `${PROFILES}/${profileId}/person-signals`, {
    item_ref: itemRef,
    signal,
    played_s: playedS ?? null,
  });
}

/** POST /profiles/{id}/reactions: the caregiver's reaction from inside Person mode. */
export function reactToCard(
  profileId: string,
  itemRef: string,
  reaction: Reaction,
): Promise<FeedbackResult> {
  return apiRequest<FeedbackResult>("POST", `${PROFILES}/${profileId}/reactions`, {
    item_ref: itemRef,
    reaction,
  });
}
