import { useState } from "react";

import type { ShelfItem } from "@/shared/api/person";
import { Button } from "@/shared/ui/button";
import { ErrorBanner, LoadingState } from "@/shared/ui/states";

import { useFirstWarmupPair, useNextWarmupPair } from "./hooks";
import { PersonCard } from "./PersonCard";

interface Step {
  pair: ShelfItem[];
  shown: string[];
}

/**
 * "This or that": two large cards at a time. A tap records the choice and shows the next pair.
 * The card not chosen gets no signal. It ends with a tap through to the shelf.
 */
export function Warmup({ profileId, onDone }: { profileId: string; onDone: () => void }) {
  const first = useFirstWarmupPair(profileId);
  const next = useNextWarmupPair(profileId);
  const [step, setStep] = useState<Step | null>(null);
  const [finished, setFinished] = useState(false);

  if (first.isPending) {
    return <LoadingState label="Getting the cards ready…" />;
  }
  if (first.isError) {
    return (
      <ErrorBanner
        error={first.error}
        title="Couldn't start the warm-up"
        onRetry={() => void first.refetch()}
      />
    );
  }
  const current: Step | null =
    step ??
    (first.data.pair ? { pair: first.data.pair, shown: first.data.pair.map((c) => c.ref) } : null);

  if (finished || first.data.done || current === null) {
    return (
      <Button size="lg" className="h-40 w-full max-w-xl text-4xl" onClick={onDone}>
        To the shelf
      </Button>
    );
  }

  const choose = (card: ShelfItem) => {
    next.mutate(
      { chosenRef: card.ref, shownRefs: current.shown },
      {
        onSuccess: (result) => {
          if (result.done || !result.pair) {
            setFinished(true);
            return;
          }
          setStep({
            pair: result.pair,
            shown: [...current.shown, ...result.pair.map((c) => c.ref)],
          });
        },
      },
    );
  };

  return (
    <div className="flex w-full max-w-5xl flex-col gap-6">
      {next.isError && (
        <ErrorBanner error={next.error} title="Couldn't save that" onRetry={() => next.reset()} />
      )}
      <div className="grid w-full grid-cols-1 gap-6 md:grid-cols-2">
        {current.pair.map((card) => (
          <PersonCard
            key={card.ref}
            card={card}
            disabled={next.isPending}
            onChoose={() => choose(card)}
            className="min-h-72"
          />
        ))}
      </div>
    </div>
  );
}
