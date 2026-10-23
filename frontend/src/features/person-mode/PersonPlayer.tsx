import { useState } from "react";

import { MediaStage } from "@/features/player/MediaStage";
import { usePlayback } from "@/features/player/usePlayback";
import type { ShelfItem } from "@/shared/api/person";
import { Button } from "@/shared/ui/button";

import { CaregiverReactions } from "./CaregiverReactions";
import { usePersonSignal } from "./hooks";

// A stop before this many seconds counts as a skip, which only lowers the item's ranking.
const SKIP_UNDER_SECONDS = 15;

interface PersonPlayerProps {
  profileId: string;
  card: ShelfItem;
  onClose: () => void;
}

/**
 * The full-screen player: a huge Stop, Play, Play again and ♥. Nothing plays until it's tapped,
 * and it never moves on to another item by itself. Give it a `key` per card.
 */
export function PersonPlayer({ profileId, card, onClose }: PersonPlayerProps) {
  const playback = usePlayback(card.media);
  const signal = usePersonSignal(profileId);
  const [loved, setLoved] = useState(false);
  const playing = playback.status === "playing";
  const unusable = playback.status === "loading" || playback.status === "error";

  const stop = () => {
    const played = Math.floor(playback.elapsed);
    if (played < SKIP_UNDER_SECONDS) {
      signal.mutate({ itemRef: card.ref, signal: "skipped", playedS: played });
    }
    playback.stop();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-20 flex flex-col gap-4 overflow-auto bg-background p-4 text-2xl sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <h1 className="font-serif text-4xl font-semibold">{card.title}</h1>
        <CaregiverReactions profileId={profileId} card={card} onHidden={onClose} />
      </div>
      <MediaStage media={card.media} playback={playback} className="max-h-[50dvh]" />
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Button
          variant="destructive"
          className="col-span-2 h-28 text-4xl sm:col-span-1"
          onClick={stop}
        >
          Stop
        </Button>
        <Button
          className="h-28 text-4xl"
          disabled={unusable}
          onClick={playing ? playback.pause : playback.play}
        >
          {playing ? "Pause" : "Play"}
        </Button>
        <Button
          variant="outline"
          className="h-28 text-3xl"
          disabled={unusable}
          onClick={() => {
            playback.restart();
            signal.mutate({ itemRef: card.ref, signal: "replayed" });
          }}
        >
          Play again
        </Button>
        <Button
          variant={loved ? "default" : "outline"}
          className="h-28 text-5xl"
          aria-label={loved ? "Loved" : "Love this"}
          aria-pressed={loved}
          onClick={() => {
            if (!loved) {
              setLoved(true);
              signal.mutate({ itemRef: card.ref, signal: "loved" });
            }
          }}
        >
          {loved ? "♥" : "♡"}
        </Button>
      </div>
    </div>
  );
}
