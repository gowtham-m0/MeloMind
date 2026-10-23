import { apiRequest } from "./client";
import type { FavouriteKind } from "./profiles";
import type { components } from "./schema";

/** A taste-search match: what the caregiver taps to save a verified favourite. */
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
