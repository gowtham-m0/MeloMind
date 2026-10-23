import type { ShelfItem } from "@/shared/api/person";
import { ErrorBanner, LoadingState } from "@/shared/ui/states";

import { usePersonSignal, useShelf } from "./hooks";
import { PersonCard } from "./PersonCard";

interface ShelfProps {
  profileId: string;
  onPlay: (card: ShelfItem) => void;
}

/** Large cards to choose from. A tap is a choice, and opens the player. */
export function Shelf({ profileId, onPlay }: ShelfProps) {
  const shelf = useShelf(profileId);
  const signal = usePersonSignal(profileId);

  if (shelf.isPending) {
    return <LoadingState label="Getting the cards ready…" />;
  }
  if (shelf.isError) {
    return (
      <ErrorBanner
        error={shelf.error}
        title="Couldn't load the cards"
        onRetry={() => void shelf.refetch()}
      />
    );
  }
  if (shelf.data.length === 0) {
    return <p className="text-center text-3xl">Nothing here yet.</p>;
  }
  return (
    <ul className="grid w-full max-w-5xl grid-cols-1 gap-6 self-start sm:grid-cols-2 lg:grid-cols-3">
      {shelf.data.map((card) => (
        <li key={card.ref}>
          <PersonCard
            card={card}
            onChoose={() => {
              signal.mutate({ itemRef: card.ref, signal: "chose" });
              onPlay(card);
            }}
          />
        </li>
      ))}
    </ul>
  );
}
