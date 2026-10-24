import { apiRequest } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

/** A feed snapshot: hero, rows and the sidebar's taste tags. */
export type Feed = Schemas["FeedOut"];
/** One row of cards. `rail` rows show in the right rail. */
export type FeedRow = Schemas["FeedRowOut"];
/** One card. */
export type FeedItem = Schemas["FeedItemOut"];
/** Where to find an item: "Search on …" or a direct "Open on …". */
export type PlatformLink = Schemas["PlatformLinkOut"];
/** A card with "More like this". */
export type ItemDetail = Schemas["ItemDetailOut"];
/** A YouTube video for the optional preview. */
export type Preview = Schemas["PreviewOut"];
/** What a signal did. */
export type FeedbackResult = Schemas["FeedbackOut"];
/** A signal the app may send. */
export type ClientSignal = Schemas["FeedbackIn"]["signal"];
/** Liked and saved items. */
export type Library = Schemas["LibraryOut"];
/** An item marked "not interested". */
export type Exclusion = Schemas["ExclusionOut"];
/** The next pair of the taste quiz. */
export type QuizStep = Schemas["QuizStepOut"];
/** An agent run and its plain-English log. */
export type AgentRun = Schemas["AgentRunOut"];

const profileUrl = (profileId: string) => `/api/v1/profiles/${profileId}`;

/** GET /profiles/{id}/feed: the newest finished feed (404 when there's none yet). */
export function getFeed(profileId: string): Promise<Feed> {
  return apiRequest<Feed>("GET", `${profileUrl(profileId)}/feed`);
}

/** POST /profiles/{id}/feed/refresh: starts a build, or returns the one already running. */
export function refreshFeed(profileId: string): Promise<Feed> {
  return apiRequest<Feed>("POST", `${profileUrl(profileId)}/feed/refresh`);
}

/** GET /agent-runs/{id}: the run's status and log, polled while it works. */
export function getRun(runId: string): Promise<AgentRun> {
  return apiRequest<AgentRun>("GET", `/api/v1/agent-runs/${runId}`);
}

/** GET /profiles/{id}/items/{ref}: the item and more like it. */
export function getItem(profileId: string, ref: string): Promise<ItemDetail> {
  return apiRequest<ItemDetail>("GET", `${profileUrl(profileId)}/items/${encodeURIComponent(ref)}`);
}

/** POST /profiles/{id}/items/{ref}/preview: a YouTube video, looked up on demand. */
export function previewItem(profileId: string, ref: string): Promise<Preview> {
  return apiRequest<Preview>(
    "POST",
    `${profileUrl(profileId)}/items/${encodeURIComponent(ref)}/preview`,
  );
}

/** POST /profiles/{id}/feedback: like, save, open, dislike or dismiss an item. */
export function sendFeedback(
  profileId: string,
  item: Pick<FeedItem, "ref" | "title" | "entity_type">,
  signal: ClientSignal,
  platform?: string,
): Promise<FeedbackResult> {
  return apiRequest<FeedbackResult>("POST", `${profileUrl(profileId)}/feedback`, {
    ref: item.ref,
    title: item.title,
    entity_type: item.entity_type,
    signal,
    platform,
  });
}

/** GET /profiles/{id}/library: liked and saved items. */
export function getLibrary(profileId: string): Promise<Library> {
  return apiRequest<Library>("GET", `${profileUrl(profileId)}/library`);
}

/** GET /profiles/{id}/exclusions: the not-interested list. */
export function listExclusions(profileId: string): Promise<Exclusion[]> {
  return apiRequest<Exclusion[]>("GET", `${profileUrl(profileId)}/exclusions`);
}

/** DELETE /profiles/{id}/exclusions/{exclusionId}: undo a "not interested". */
export function removeExclusion(profileId: string, exclusionId: string): Promise<Exclusion[]> {
  return apiRequest<Exclusion[]>("DELETE", `${profileUrl(profileId)}/exclusions/${exclusionId}`);
}

/** POST /profiles/{id}/quiz/next: record a pick and get the next pair. */
export function quizNext(
  profileId: string,
  shownRefs: string[],
  pickedRef?: string,
): Promise<QuizStep> {
  return apiRequest<QuizStep>("POST", `${profileUrl(profileId)}/quiz/next`, {
    picked_ref: pickedRef,
    shown_refs: shownRefs,
  });
}
