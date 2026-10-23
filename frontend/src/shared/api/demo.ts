import { apiRequest } from "./client";
import type { components } from "./schema";

/** The IDs of the user's sample profiles. */
export type DemoSeedResponse = components["schemas"]["DemoSeedResponse"];

/** POST /demo/seed: creates the sample profiles for this user, once. */
export function seedDemo(): Promise<DemoSeedResponse> {
  return apiRequest<DemoSeedResponse>("POST", "/api/v1/demo/seed");
}
