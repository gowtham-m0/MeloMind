import { useCallback, useEffect, useRef, useState } from "react";

import type { Media } from "@/shared/api/sessions";

import {
  PLAYER_STATE,
  createPlayer,
  hideCaptions,
  loadYouTubeApi,
  type YouTubePlayer,
} from "./youtube";

/** Where playback is. Nothing ever starts on its own: `play` needs a tap. */
export type PlaybackStatus = "loading" | "ready" | "playing" | "paused" | "ended" | "error";

/** Controls for one item's media, whether a YouTube video or demo stand-in media. */
export interface Playback {
  status: PlaybackStatus;
  /** Seconds played so far. */
  elapsed: number;
  play: () => void;
  pause: () => void;
  /** Stops and goes back to the start. */
  stop: () => void;
  /** Plays again from the start. */
  restart: () => void;
  /** Attach to the element the YouTube player should fill. */
  attachPlayer: (element: HTMLDivElement | null) => void;
}

const TICK_MS = 500;

function statusFor(state: number): PlaybackStatus | null {
  switch (state) {
    case PLAYER_STATE.PLAYING:
    case PLAYER_STATE.BUFFERING:
      return "playing";
    case PLAYER_STATE.PAUSED:
      return "paused";
    case PLAYER_STATE.ENDED:
      return "ended";
    case PLAYER_STATE.CUED:
      return "ready";
    default:
      return null;
  }
}

/**
 * Playback for one item. Give the component that calls this a `key` per item, so each item
 * starts fresh. Demo media plays as a timer, with no video.
 */
export function usePlayback(media: Media | null): Playback {
  const provider = media?.provider ?? null;
  const videoId = media?.ref ?? null;
  const duration = media?.duration_s ?? 0;
  const isYouTube = provider === "youtube";
  const [rawStatus, setStatus] = useState<PlaybackStatus>(isYouTube ? "loading" : "ready");
  const [elapsed, setElapsed] = useState(0);
  const [host, setHost] = useState<HTMLDivElement | null>(null);
  const player = useRef<YouTubePlayer | null>(null);
  // Demo media ends when its time is up; a YouTube video reports its own end.
  const finished = !isYouTube && duration > 0 && elapsed >= duration;
  const status: PlaybackStatus = finished && rawStatus === "playing" ? "ended" : rawStatus;

  useEffect(() => {
    if (!isYouTube || !host || !videoId) {
      return;
    }
    let cancelled = false;
    let created: YouTubePlayer | null = null;
    const target = document.createElement("div");
    host.append(target);
    loadYouTubeApi()
      .then((api) => {
        if (cancelled) {
          return;
        }
        created = createPlayer(api, target, videoId, {
          onReady: () => setStatus("ready"),
          onStateChange: (event) => {
            const next = statusFor(event.data);
            if (next === "playing" && created) {
              hideCaptions(created);
            }
            if (next) {
              setStatus(next);
            }
          },
          onError: () => setStatus("error"),
        });
        player.current = created;
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
      created?.destroy();
      player.current = null;
      host.replaceChildren();
    };
  }, [isYouTube, host, videoId]);

  useEffect(() => {
    if (status !== "playing") {
      return;
    }
    const timer = window.setInterval(() => {
      if (isYouTube) {
        setElapsed(player.current?.getCurrentTime() ?? 0);
        return;
      }
      setElapsed((seconds) => Math.min(seconds + TICK_MS / 1000, duration));
    }, TICK_MS);
    return () => window.clearInterval(timer);
  }, [status, isYouTube, duration]);

  const play = useCallback(() => {
    if (isYouTube) {
      player.current?.playVideo();
      return;
    }
    if (finished) {
      setElapsed(0);
    }
    setStatus("playing");
  }, [isYouTube, finished]);

  const pause = useCallback(() => {
    if (isYouTube) {
      player.current?.pauseVideo();
    } else {
      setStatus("paused");
    }
  }, [isYouTube]);

  const stop = useCallback(() => {
    player.current?.stopVideo();
    setElapsed(0);
    setStatus("ready");
  }, []);

  const restart = useCallback(() => {
    setElapsed(0);
    if (isYouTube) {
      player.current?.seekTo(0, true);
      player.current?.playVideo();
    } else {
      setStatus("playing");
    }
  }, [isYouTube]);

  return { status, elapsed, play, pause, stop, restart, attachPlayer: setHost };
}
