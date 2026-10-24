import { BookOpen, Clapperboard, Music2, RefreshCw, Sparkles, type LucideIcon } from "lucide-react";
import { useState } from "react";

import { Button } from "@/shared/ui/button";
import { ToggleChip } from "@/shared/ui/chip";

const MOODS = ["Chill", "Happy", "Focused", "Melancholy", "Energetic"];

/** "Your vibe today": pick a mood. Mood rows arrive with the agent's Ask feature (Phase 4), so
 * the button says so plainly instead of pretending. */
export function VibePanel() {
  const [mood, setMood] = useState<string | null>(null);
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
            key={option}
            selected={mood === option}
            onClick={() => setMood(mood === option ? null : option)}
          >
            {option}
          </ToggleChip>
        ))}
      </div>
      <Button variant="secondary" className="mt-4 w-full" disabled>
        <Sparkles /> Mood picks are coming soon
      </Button>
    </section>
  );
}

interface QuickAction {
  label: string;
  icon: LucideIcon;
  onSelect: () => void;
}

/** Shortcuts down the feed, and a fresh build. */
export function QuickActions({
  onJump,
  onRefresh,
}: {
  onJump: (rowKey: string) => void;
  onRefresh: () => void;
}) {
  const actions: QuickAction[] = [
    { label: "Watch something new", icon: Clapperboard, onSelect: () => onJump("films") },
    { label: "Find a book to read", icon: BookOpen, onSelect: () => onJump("books") },
    { label: "Play new music", icon: Music2, onSelect: () => onJump("music") },
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
