import { apiRequest } from "./client";
import type { components } from "./schema";

/** An item the caregiver rejected, or hid because it upset them. */
export type Exclusion = components["schemas"]["ExclusionOut"];

const PROFILES = "/api/v1/profiles";

/** GET /profiles/{id}/exclusions. */
export function listExclusions(profileId: string): Promise<Exclusion[]> {
  return apiRequest<Exclusion[]>("GET", `${PROFILES}/${profileId}/exclusions`);
}

/** DELETE /profiles/{id}/exclusions/{exclusionId}: lets an item back in after review. */
export function removeExclusion(profileId: string, exclusionId: string): Promise<Exclusion[]> {
  return apiRequest<Exclusion[]>("DELETE", `${PROFILES}/${profileId}/exclusions/${exclusionId}`);
}
