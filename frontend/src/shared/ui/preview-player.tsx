import { cn } from "cn";
import { Pause, Play } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

interface PreviewApi {
  /** The ref of the song playing now, if any. */
  playingRef: string | null;
  /** How far through the preview, 0 to 1. */
  progress: number;
  /** Play this song's preview, or pause it when it's the one playing. */
  toggle: (ref: string, url: string) => void;
  stop: () => void;
  /** Stop only if this song is the one playing. */
  stopIf: (ref: string) => void;
}

const PreviewContext = createContext<PreviewApi | null>(null);

/**
 * One audio element for the whole app, so only one 30-second preview plays at a time. Previews
 * are Apple's: streamed on tap only (no autoplay, rule 6), never downloaded or stored.
 */
export function PreviewPlayerProvider({ children }: { children: ReactNode }) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const [playingRef, setPlayingRef] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  // The song playing now, readable from callbacks without re-creating them.
  const current = useRef<string | null>(null);

  const stop = useCallback(() => {
    audio.current?.pause();
    current.current = null;
    setPlayingRef(null);
    setProgress(0);
  }, []);

  const stopIf = useCallback(
    (ref: string) => {
      if (current.current === ref) {
        stop();
      }
    },
    [stop],
  );

  const element = useCallback(() => {
    if (!audio.current) {
      const created = new Audio();
      created.preload = "none";
      created.addEventListener("timeupdate", () => {
        if (created.duration > 0) {
          setProgress(created.currentTime / created.duration);
        }
      });
      created.addEventListener("ended", () => {
        current.current = null;
        setPlayingRef(null);
        setProgress(0);
      });
      audio.current = created;
    }
    return audio.current;
  }, []);

  const toggle = useCallback(
    (ref: string, url: string) => {
      if (current.current === ref) {
        stop();
        return;
      }
      const player = element();
      player.src = url;
      current.current = ref;
      setPlayingRef(ref);
      setProgress(0);
      player.play().catch(() => {
        if (current.current === ref) {
          current.current = null;
          setPlayingRef(null);
        }
      });
    },
    [element, stop],
  );

  useEffect(() => () => audio.current?.pause(), []);

  const value = useMemo(
    () => ({ playingRef, progress, toggle, stop, stopIf }),
    [playingRef, progress, toggle, stop, stopIf],
  );
  return <PreviewContext.Provider value={value}>{children}</PreviewContext.Provider>;
}

/** The app's preview player. */
export function usePreviewPlayer(): PreviewApi {
  const api = useContext(PreviewContext);
  if (!api) {
    throw new Error("usePreviewPlayer needs a PreviewPlayerProvider.");
  }
  return api;
}

interface PreviewButtonProps {
  songRef: string;
  url: string;
  title: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZES = { sm: "size-11", md: "size-11", lg: "size-14" };
const RING = 2 * Math.PI * 46;

/**
 * Play or pause a song's 30-second preview, with a ring that fills as it plays. The preview stops
 * when the button leaves the screen, so it never plays away from its store link.
 */
export function PreviewButton({ songRef, url, title, size = "md", className }: PreviewButtonProps) {
  const { playingRef, progress, toggle, stopIf } = usePreviewPlayer();
  const playing = playingRef === songRef;

  useEffect(() => () => stopIf(songRef), [songRef, stopIf]);

  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        toggle(songRef, url);
      }}
      aria-pressed={playing}
      aria-label={
        playing ? `Pause the preview of ${title}` : `Play a 30-second preview of ${title}`
      }
      className={cn(
        "relative grid shrink-0 place-items-center rounded-full bg-ink text-white shadow-soft transition-transform duration-150 ease-(--ease-out) active:scale-95",
        SIZES[size],
        className,
      )}
    >
      <svg aria-hidden viewBox="0 0 100 100" className="absolute inset-0 size-full -rotate-90">
        <circle
          cx="50"
          cy="50"
          r="46"
          fill="none"
          stroke="var(--primary)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={RING}
          strokeDashoffset={RING * (1 - (playing ? progress : 0))}
          className={cn("transition-opacity duration-200", playing ? "opacity-100" : "opacity-0")}
        />
      </svg>
      {playing ? (
        <Pause className="size-[45%] fill-current" strokeWidth={0} />
      ) : (
        <Play className="ml-[6%] size-[45%] fill-current" strokeWidth={0} />
      )}
    </button>
  );
}
