import { getAccessToken } from "./supabase";

const baseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "");

type Method = "GET" | "POST" | "PATCH" | "DELETE";

interface ErrorBody {
  error?: unknown;
  detail?: unknown;
}

/** A failed API call: carries the backend's `{ error, detail }` when it sent one. */
export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string | null;

  constructor(message: string, status: number | null, code: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/**
 * Calls the backend with the signed-in user's token, sending `body` as JSON.
 * Resolves to undefined for 204 responses. Throws ApiError on a network failure or a non-2xx status.
 */
export async function apiRequest<T>(method: Method, path: string, body?: unknown): Promise<T> {
  if (!baseUrl) {
    throw new ApiError("VITE_API_BASE_URL is not set. Copy .env.example to .env.local.", null);
  }

  const headers: Record<string, string> = { Accept: "application/json" };
  const token = await getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Could not reach the backend.", null);
  }

  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** GETs JSON from the backend. */
export function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>("GET", path);
}

async function toApiError(response: Response): Promise<ApiError> {
  const body = await readErrorBody(response);
  const code = typeof body.error === "string" ? body.error : null;
  if (typeof body.detail === "string") {
    return new ApiError(body.detail, response.status, code);
  }
  if (response.status === 422) {
    return new ApiError("Some details aren't valid. Please check and try again.", 422, code);
  }
  return new ApiError(`Request failed (${response.status}).`, response.status, code);
}

async function readErrorBody(response: Response): Promise<ErrorBody> {
  try {
    const body: unknown = await response.json();
    return typeof body === "object" && body !== null ? (body as ErrorBody) : {};
  } catch {
    return {};
  }
}
