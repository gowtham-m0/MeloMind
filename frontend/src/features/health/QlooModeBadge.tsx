import { useHealth } from "./useHealth";

/** "Demo data" or "Live Qloo": where search results and recommendations come from. */
export function QlooModeBadge() {
  const health = useHealth();

  if (!health.isSuccess) {
    return null;
  }
  const live = health.data.qloo_mode === "live";
  return (
    <span className="inline-flex items-center rounded-full border-2 border-current px-3 text-base font-bold text-destructive">
      {live ? "Live Qloo" : "Demo data"}
    </span>
  );
}
