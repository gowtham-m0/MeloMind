import { apiGet } from "./client";
import type { components } from "./schema";

/** The backend's health check, typed from the generated OpenAPI schema. */
export type HealthResponse = components["schemas"]["HealthResponse"];

/** Reads GET /api/v1/health. */
export function getHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/api/v1/health");
}
