import { apiRequest } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

/** What to ask the agent for: words, a mood or a surprise. */
export type AskRequest = Schemas["AskIn"];
/** A mood from "Your vibe today". */
export type Mood = NonNullable<AskRequest["mood"]>;
/** What two tastes share, a 0 to 1 score and the "For you both" row. */
export type TasteMatch = Schemas["TasteMatchOut"];

const profileUrl = (profileId: string) => `/api/v1/profiles/${profileId}`;

/** POST /profiles/{id}/ask: starts a run whose result is one extra row. Poll the run. */
export function askAgent(profileId: string, body: AskRequest): Promise<{ agent_run_id: string }> {
  return apiRequest<{ agent_run_id: string }>("POST", `${profileUrl(profileId)}/ask`, body);
}

/** POST /profiles/{id}/taste-match: compare with another profile, or a friend's favourites. */
export function matchTastes(
  profileId: string,
  body: { other_profile_id?: string; favourites?: string[] },
): Promise<TasteMatch> {
  return apiRequest<TasteMatch>("POST", `${profileUrl(profileId)}/taste-match`, body);
}
