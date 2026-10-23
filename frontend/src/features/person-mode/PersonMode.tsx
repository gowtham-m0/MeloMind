import { useState } from "react";

import type { ShelfItem } from "@/shared/api/person";

import { PersonPlayer } from "./PersonPlayer";
import { Shelf } from "./Shelf";
import { Warmup } from "./Warmup";
import { WarmupSetup } from "./WarmupSetup";

type Stage =
  { name: "setup" } | { name: "warmup" } | { name: "shelf" } | { name: "playing"; card: ShelfItem };

/**
 * Person mode: the caregiver's setup step, then the warm-up, the shelf and the player. There's
 * no typing, search, menu or AI-written text here; only approved items are shown.
 */
export function PersonMode({ profileId }: { profileId: string }) {
  const [stage, setStage] = useState<Stage>({ name: "setup" });
  const toShelf = () => setStage({ name: "shelf" });

  switch (stage.name) {
    case "setup":
      return (
        <WarmupSetup
          profileId={profileId}
          onHandOver={() => setStage({ name: "warmup" })}
          onSkip={toShelf}
        />
      );
    case "warmup":
      return <Warmup profileId={profileId} onDone={toShelf} />;
    case "shelf":
      return <Shelf profileId={profileId} onPlay={(card) => setStage({ name: "playing", card })} />;
    case "playing":
      return (
        <PersonPlayer
          key={stage.card.ref}
          profileId={profileId}
          card={stage.card}
          onClose={toShelf}
        />
      );
  }
}
