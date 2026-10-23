import { cn } from "cn";

import type { Media } from "@/shared/api/sessions";

import { formatClock } from "./format";
import type { Playback } from "./usePlayback";

interface MediaStageProps {
  media: Media;
  playback: Playback;
  className?: string;
}

/**
 * Where an item plays: the YouTube player, or a plain card for demo stand-in media. The video
 * never starts on its own; the controls around it do that.
 */
export function MediaStage({ media, playback, className }: MediaStageProps) {
  const { status, elapsed, attachPlayer } = playback;

  if (media.provider !== "youtube") {
    const percent = media.duration_s > 0 ? Math.min((elapsed / media.duration_s) * 100, 100) : 0;
    return (
      <div
        className={cn(
          "flex aspect-video w-full flex-col items-center justify-center gap-4 rounded-lg border-2 bg-secondary p-6 text-center",
          className,
        )}
      >
        <span className="rounded-full border-2 border-destructive px-3 text-base font-bold text-destructive">
          Demo media
        </span>
        <p className="max-w-prose text-xl">{media.title}</p>
        <div className="h-3 w-full max-w-md overflow-hidden rounded-full bg-background">
          <div className="h-full bg-primary" style={{ width: `${percent}%` }} />
        </div>
        <p className="text-muted-foreground">
          {formatClock(elapsed)} / {formatClock(media.duration_s)}
        </p>
      </div>
    );
  }

  return (
    <div
      className={cn("relative aspect-video w-full overflow-hidden rounded-lg bg-black", className)}
    >
      <div ref={attachPlayer} className="absolute inset-0 [&_iframe]:h-full [&_iframe]:w-full" />
      {status === "loading" && (
        <p role="status" className="absolute inset-0 flex items-center justify-center text-white">
          Loading the video…
        </p>
      )}
      {status === "error" && (
        <p
          role="alert"
          className="absolute inset-0 flex items-center justify-center bg-black p-6 text-center text-white"
        >
          This video can't play here. Try the next item.
        </p>
      )}
    </div>
  );
}
