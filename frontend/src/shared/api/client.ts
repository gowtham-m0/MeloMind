const baseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "");

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

/** GETs JSON from the backend. Throws ApiError on a network failure or a non-2xx status. */
export async function apiGet<T>(path: string): Promise<T> {
  if (!baseUrl) {
    throw new ApiError("VITE_API_BASE_URL is not set. Copy .env.example to .env.local.", null);
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError("Could not reach the backend.", null);
  }

  if (!response.ok) {
    const body = await readErrorBody(response);
    const detail =
      typeof body.detail === "string" ? body.detail : `Request failed (${response.status}).`;
    const code = typeof body.error === "string" ? body.error : null;
    throw new ApiError(detail, response.status, code);
  }
  return (await response.json()) as T;
}

async function readErrorBody(response: Response): Promise<ErrorBody> {
  try {
    const body: unknown = await response.json();
    return typeof body === "object" && body !== null ? (body as ErrorBody) : {};
  } catch {
    return {};
  }
}
