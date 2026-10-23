import { useState } from "react";

import { ReactionButtons } from "@/features/sessions/ReactionButtons";
import type { ShelfItem } from "@/shared/api/person";
import type { Reaction } from "@/shared/api/sessions";
import { useLongPress } from "@/shared/hooks/useLongPress";
import { Button } from "@/shared/ui/button";

import { useReactToCard } from "./hooks";

const HOLD_MS = 1500;
const HIDING: Reaction[] = ["upset", "rejected"];

interface CaregiverReactionsProps {
  profileId: string;
  card: ShelfItem;
  /** Called after the caregiver hid or rejected the card, so the player can close. */
  onHidden: () => void;
}

/**
 * A small button for the caregiver: hold it to open the reaction buttons, so an upsetting item
 * can be hidden at once. A tap does nothing, so the person can't open it by accident.
 */
export function CaregiverReactions({ profileId, card, onHidden }: CaregiverReactionsProps) {
  const [open, setOpen] = useState(false);
  const react = useReactToCard(profileId);
  const press = useLongPress(() => setOpen(true), HOLD_MS);

  if (!open) {
    return (
      <button
        type="button"
        {...press.handlers}
        className="relative min-h-11 overflow-hidden rounded-md border-2 px-3 text-base text-muted-foreground"
      >
        <span
          aria-hidden="true"
          className="absolute inset-y-0 left-0 bg-secondary"
          style={{ width: `${press.progress * 100}%` }}
        />
        <span className="relative">Caregiver (hold)</span>
      </button>
    );
  }
  return (
    <div
      role="dialog"
      aria-label="Caregiver reactions"
      className="fixed inset-x-4 bottom-4 z-30 mx-auto flex max-w-2xl flex-col gap-3 rounded-lg border-2 bg-card p-4 text-lg shadow-lg"
    >
      <ReactionButtons
        title={card.title}
        onReact={async (reaction) => {
          const result = await react.mutateAsync({ itemRef: card.ref, reaction });
          if (HIDING.includes(reaction)) {
            onHidden();
          }
          return result;
        }}
      />
      <Button variant="outline" className="self-end" onClick={() => setOpen(false)}>
        Close
      </Button>
    </div>
  );
}
