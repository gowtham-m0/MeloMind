import { cn } from "cn";

import type { SessionItem } from "@/shared/api/sessions";

const LABELS: Record<SessionItem["source"], string> = {
  qloo_live: "Live Qloo",
  demo_fixture: "Demo data",
  favourite: "Favourite",
};

/** Where an item came from: live Qloo, the demo fixtures or a favourite. */
export function SourceBadge({ source }: { source: SessionItem["source"] }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border-2 px-3 text-base font-bold",
        source === "demo_fixture"
          ? "border-destructive text-destructive"
          : "border-primary text-primary",
      )}
    >
      {LABELS[source]}
    </span>
  );
}
