import { cn } from "cn";
import type { ComponentProps } from "react";

import { TYPE_META, type ItemType } from "./types";

/** A small label with the type's colour dot: "● Film". */
export function TypeChip({ type, className }: { type: ItemType; className?: string }) {
  const meta = TYPE_META[type];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs font-semibold tracking-wide uppercase",
        meta.text,
        className,
      )}
    >
      <span aria-hidden className={cn("size-1.5 rounded-full", meta.dot)} />
      {meta.label}
    </span>
  );
}

/** A quiet pill for tags and taste-profile chips. */
export function TagChip({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "inline-flex h-8 items-center rounded-full border border-line bg-surface px-3 text-sm text-body",
        className,
      )}
      {...props}
    />
  );
}

type ToggleChipProps = ComponentProps<"button"> & { selected: boolean };

/** A pill toggle, such as a mood chip: selected is amber with ink text. */
export function ToggleChip({ selected, className, ...props }: ToggleChipProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cn(
        "inline-flex h-10 items-center rounded-full border px-4 text-sm font-medium transition-colors duration-200",
        selected
          ? "border-primary bg-primary text-ink"
          : "border-line bg-surface text-body hover:border-[#c9c9c9] hover:text-ink",
        className,
      )}
      {...props}
    />
  );
}

/** "Live Qloo", "Demo data" or, for a song (a catalogue lookup for a Qloo-picked artist),
 * "Song via iTunes", so nobody mistakes where an item came from. */
export function SourceBadge({ source }: { source: string }) {
  if (source === "song_catalogue") {
    return (
      <span className="inline-flex h-6 items-center gap-1.5 rounded-full bg-music/15 px-2.5 text-xs font-semibold whitespace-nowrap text-music-ink">
        <span aria-hidden className="size-1.5 rounded-full bg-music" />
        Song via iTunes
      </span>
    );
  }
  const demo = source === "demo_fixture";
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center gap-1.5 rounded-full px-2.5 text-xs font-semibold whitespace-nowrap",
        demo ? "bg-surface-2 text-muted" : "bg-book/12 text-book-ink",
      )}
    >
      <span aria-hidden className={cn("size-1.5 rounded-full", demo ? "bg-muted" : "bg-book")} />
      {demo ? "Demo data" : "Live Qloo"}
    </span>
  );
}
