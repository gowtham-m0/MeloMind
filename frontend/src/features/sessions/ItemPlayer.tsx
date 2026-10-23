import type { ReactNode } from "react";

import { MediaStage } from "@/features/player/MediaStage";
import { usePlayback } from "@/features/player/usePlayback";
import type { FeedbackResult, Reaction, SessionItem } from "@/shared/api/sessions";
import { Button } from "@/shared/ui/button";
import { ITEM_TYPE_LABELS, TypeIcon } from "@/shared/ui/type-icon";

import { ageLine } from "./labels";
import { ReactionButtons } from "./ReactionButtons";

interface ItemPlayerProps {
  item: SessionItem;
  firstName: string;
  onReact: (reaction: Reaction) => Promise<FeedbackResult>;
  /** Moving between items, shown in the bar next to Stop. */
  navigation: ReactNode;
}

/**
 * One item in the caregiver's player. Give it a `key` per item so playback starts fresh. It
 * never autoplays, and Stop stays on screen at the bottom.
 */
export function ItemPlayer({ item, firstName, onReact, navigation }: ItemPlayerProps) {
  const playback = usePlayback(item.media);
  const playing = playback.status === "playing";
  const age = ageLine(item, firstName);
  const idle = !item.media || playback.status === "loading" || playback.status === "error";

  return (
    <div className="flex flex-col gap-5 pb-48 sm:pb-32">
      <div className="flex flex-wrap items-center gap-3">
        <TypeIcon type={item.entity_type} className="size-7 text-primary" />
        <h2 className="text-3xl font-semibold">{item.title}</h2>
      </div>
      <p className="text-muted-foreground">
        {ITEM_TYPE_LABELS[item.entity_type]}
        {item.release_year != null && ` · ${item.release_year}`}
        {age && ` · ${age}`}
      </p>
      {item.media ? (
        <MediaStage media={item.media} playback={playback} />
      ) : (
        <div className="flex flex-col gap-2 rounded-lg border-2 bg-secondary p-6">
          <p className="text-xl font-semibold">A book to talk about</p>
          <p>There's no video for this one. Take a few minutes to chat about it together.</p>
        </div>
      )}
      {item.prompt && (
        <div className="rounded-lg border-2 border-primary bg-card p-4">
          <p className="text-base font-semibold text-primary">You could ask</p>
          <p className="text-xl">“{item.prompt}”</p>
        </div>
      )}
      <ReactionButtons title={item.title} onReact={onReact} />
      <div className="fixed inset-x-0 bottom-0 z-10 border-t-2 bg-background/95 p-3">
        <div className="mx-auto flex max-w-5xl flex-wrap justify-center gap-3">
          <Button
            size="lg"
            variant="destructive"
            className="min-w-40"
            onClick={playback.stop}
            disabled={!item.media}
          >
            Stop
          </Button>
          <Button
            size="lg"
            className="min-w-40"
            onClick={playing ? playback.pause : playback.play}
            disabled={idle}
          >
            {playing ? "Pause" : "Play"}
          </Button>
          <Button size="lg" variant="outline" onClick={playback.restart} disabled={idle}>
            Play again
          </Button>
          {navigation}
        </div>
      </div>
    </div>
  );
}
