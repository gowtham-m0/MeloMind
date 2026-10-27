import {
  BookOpen,
  Clapperboard,
  Music2,
  NotebookPen,
  RefreshCw,
  Shuffle,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import type { Mood } from "@/shared/api/ask";
import { Button } from "@/shared/ui/button";
import { ToggleChip } from "@/shared/ui/chip";

const MOODS: { value: Mood; label: string }[] = [
  { value: "chill", label: "Chill" },
  { value: "happy", label: "Happy" },
  { value: "focused", label: "Focused" },
  { value: "melancholy", label: "Melancholy" },
  { value: "energetic", label: "Energetic" },
];

/** "Your vibe today": pick a mood and the agent builds a row of picks to match. */
export function VibePanel({
  busy,
  onGo,
}: {
  busy: boolean;
  onGo: (mood: Mood, label: string) => void;
}) {
  const [mood, setMood] = useState<Mood | null>(null);
  return (
    <section
      aria-labelledby="vibe-title"
      className="rounded-xl border border-hairline bg-surface p-4 shadow-soft"
    >
      <h2 id="vibe-title" className="text-lg font-semibold">
        Your vibe today
      </h2>
      <p className="mt-0.5 text-sm text-muted">Set the mood, get picks to match.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {MOODS.map((option) => (
          <ToggleChip
            key={option.value}
            selected={mood === option.value}
            onClick={() => setMood(mood === option.value ? null : option.value)}
          >
            {option.label}
          </ToggleChip>
        ))}
      </div>
      <Button
        className="mt-4 w-full"
        disabled={mood === null || busy}
        onClick={() => {
          const chosen = MOODS.find((option) => option.value === mood);
          if (chosen) {
            onGo(chosen.value, `${chosen.label} picks`);
          }
        }}
      >
        <Sparkles /> {busy ? "The agent is working…" : "Get recommendations"}
      </Button>
    </section>
  );
}

interface QuickAction {
  label: string;
  icon: LucideIcon;
  onSelect: () => void;
}

/** Shortcuts down the feed, the journal composer, and a fresh build. */
export function QuickActions({
  onJump,
  onRefresh,
  onJournal,
  onSurprise,
}: {
  onJump: (rowKey: string) => void;
  onRefresh: () => void;
  onJournal: () => void;
  onSurprise: () => void;
}) {
  const actions: QuickAction[] = [
    { label: "Surprise me", icon: Shuffle, onSelect: onSurprise },
    { label: "Watch something new", icon: Clapperboard, onSelect: () => onJump("films") },
    { label: "Find a book to read", icon: BookOpen, onSelect: () => onJump("books") },
    { label: "Play new music", icon: Music2, onSelect: () => onJump("music") },
    { label: "Write in your journal", icon: NotebookPen, onSelect: onJournal },
    { label: "Shake up my feed", icon: RefreshCw, onSelect: onRefresh },
  ];
  return (
    <section
      aria-labelledby="quick-title"
      className="rounded-xl border border-hairline bg-surface p-4 shadow-soft"
    >
      <h2 id="quick-title" className="text-lg font-semibold">
        Quick actions
      </h2>
      <ul className="mt-2 flex flex-col">
        {actions.map((action) => (
          <li key={action.label}>
            <button
              type="button"
              onClick={action.onSelect}
              className="flex h-12 w-full items-center gap-3 rounded-lg px-2 text-left text-[15px] font-medium text-ink transition-colors hover:bg-surface-2"
            >
              <span className="grid size-8 place-items-center rounded-lg bg-primary-tint text-primary-ink">
                <action.icon className="size-4" />
              </span>
              {action.label}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
