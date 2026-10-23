import type { Reaction, SessionItem, SessionStatus } from "@/shared/api/sessions";

/** Plain words for each status. */
export const STATUS_LABELS: Record<SessionStatus, string> = {
  planning: "Planning",
  draft: "Ready for review",
  approved: "Approved",
  in_progress: "In progress",
  completed: "Completed",
  failed: "Couldn't plan",
};

/** Plain words for each mode. */
export function modeLabel(mode: string): string {
  return mode === "warmup" ? "Warm-up set" : "Session";
}

/** The caregiver's reactions, in the order the buttons show them. */
export const REACTIONS: { value: Reaction; label: string }[] = [
  { value: "sang_along", label: "Sang along" },
  { value: "smiled", label: "Smiled" },
  { value: "calm", label: "Calm" },
  { value: "neutral", label: "No reaction" },
  { value: "upset", label: "Upset" },
  { value: "rejected", label: "Reject" },
];

/** "Margaret was 17 when this came out", or null when the year is unknown. */
export function ageLine(item: SessionItem, firstName: string): string | null {
  if (item.age_at_release == null) {
    return null;
  }
  return `${firstName} was ${item.age_at_release} when this came out`;
}
