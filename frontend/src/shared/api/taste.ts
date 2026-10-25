import { apiRequest } from "./client";
import type { FavouriteKind } from "./profiles";
import type { components } from "./schema";

/** A taste-search match: what the user taps to save a verified favourite. */
export type EntityMatch = components["schemas"]["EntityMatchOut"];
/** artist, movie, tv_show or book. Qloo has no songs. */
export type EntityType = components["schemas"]["EntityType"];

/** GET /taste/search. For a song, pass kind "song" and the singer's name. */
export function searchTaste(query: string, kind?: FavouriteKind): Promise<EntityMatch[]> {
  const params = new URLSearchParams({ q: query });
  if (kind) {
    params.set("type", kind);
  }
  return apiRequest<EntityMatch[]>("GET", `/api/v1/taste/search?${params.toString()}`);
}

/** The taste page: sentence, tags, counts, favourites and recent likes. */
export type Taste = components["schemas"]["TasteOut"];
/** The taste map: nodes and confirmed links, capped. */
export type TasteMap = components["schemas"]["TasteMapOut"];
/** One node on the taste map. */
export type TasteMapNode = components["schemas"]["MapNodeOut"];

/** GET /profiles/{id}/taste. */
export function getTaste(profileId: string): Promise<Taste> {
  return apiRequest<Taste>("GET", `/api/v1/profiles/${profileId}/taste`);
}

/** GET /profiles/{id}/taste/map. */
export function getTasteMap(profileId: string): Promise<TasteMap> {
  return apiRequest<TasteMap>("GET", `/api/v1/profiles/${profileId}/taste/map`);
}

/** One match the resolver proposes. A song comes back as its singer, with the song title. */
export interface ResolveProposal {
  entity_id: string;
  name: string;
  type: EntityType;
  kind: FavouriteKind;
  year: number | null;
  image_url: string | null;
  song_title: string | null;
  why: string;
}

/** What "keep it as text" would save: names only, never what was typed. */
export interface TextFavourite {
  name: string;
  kind: FavouriteKind;
  song_title: string | null;
}

/** POST /profiles/{id}/favourites/resolve: look up a name, song or lyric. Poll the run. */
export function resolveFavourite(
  profileId: string,
  body: { text: string; kind?: FavouriteKind; hint?: string },
): Promise<{ agent_run_id: string }> {
  return apiRequest<{ agent_run_id: string }>(
    "POST",
    `/api/v1/profiles/${profileId}/favourites/resolve`,
    body,
  );
}
