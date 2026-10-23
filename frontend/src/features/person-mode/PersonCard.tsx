import { cn } from "cn";

import type { ShelfItem } from "@/shared/api/person";
import { decadeClass } from "@/shared/ui/decade";
import { ITEM_TYPE_LABELS, TypeIcon } from "@/shared/ui/type-icon";

interface PersonCardProps {
  card: ShelfItem;
  onChoose: () => void;
  disabled?: boolean;
  className?: string;
}

/**
 * A very large card: the title, a type icon, the year and the decade's colour. No reasons,
 * prompts or other AI-written text, ever. There's room at the top for an image later.
 */
export function PersonCard({ card, onChoose, disabled, className }: PersonCardProps) {
  const label = [card.title, ITEM_TYPE_LABELS[card.entity_type], card.release_year]
    .filter(Boolean)
    .join(", ");
  return (
    <button
      type="button"
      onClick={onChoose}
      disabled={disabled}
      aria-label={label}
      className={cn(
        "flex min-h-56 w-full flex-col overflow-hidden rounded-2xl border-4 border-foreground/70 bg-card text-left shadow-sm transition-transform active:scale-[0.98] disabled:opacity-60",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "flex h-24 w-full items-center justify-center text-white",
          decadeClass(card.decade),
        )}
      >
        <TypeIcon type={card.entity_type} className="size-14" />
      </span>
      <span className="flex flex-1 flex-col justify-center gap-2 p-5">
        <span className="font-serif text-3xl leading-tight font-semibold">{card.title}</span>
        {card.release_year != null && (
          <span className="text-2xl text-muted-foreground">{card.release_year}</span>
        )}
      </span>
    </button>
  );
}
