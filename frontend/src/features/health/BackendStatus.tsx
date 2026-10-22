import { useHealth } from "./useHealth";

/** Whether the backend is reachable, and whether recommendations use demo data or live Qloo. */
export function BackendStatus() {
  const health = useHealth();

  return (
    <div aria-live="polite" className="rounded-lg border p-4">
      {health.isPending && <p>Checking the backend…</p>}
      {health.isError && (
        <p>
          <strong>Backend: unreachable.</strong> {health.error.message}
        </p>
      )}
      {health.isSuccess && (
        <p className="flex flex-wrap items-center gap-3">
          <strong>Backend: {health.data.status}</strong>
          <span className="rounded-full border px-3 py-1 text-base">
            {health.data.qloo_mode === "live" ? "Live Qloo" : "Demo data"}
          </span>
        </p>
      )}
    </div>
  );
}
