/** The parts of the YouTube IFrame Player API that MeloMind uses. */
export interface YouTubePlayer {
  playVideo(): void;
  pauseVideo(): void;
  stopVideo(): void;
  seekTo(seconds: number, allowSeekAhead: boolean): void;
  unloadModule(module: string): void;
  getCurrentTime(): number;
  destroy(): void;
}

interface PlayerEvent {
  data: number;
}

interface PlayerOptions {
  videoId: string;
  width: string;
  height: string;
  playerVars: Record<string, number>;
  events: {
    onReady: () => void;
    onStateChange: (event: PlayerEvent) => void;
    onError: () => void;
  };
}

interface YouTubeNamespace {
  Player: new (element: HTMLElement, options: PlayerOptions) => YouTubePlayer;
}

declare global {
  interface Window {
    YT?: YouTubeNamespace;
    onYouTubeIframeAPIReady?: () => void;
  }
}

/** YouTube's player states. */
export const PLAYER_STATE = { ENDED: 0, PLAYING: 1, PAUSED: 2, BUFFERING: 3, CUED: 5 } as const;

const API_URL = "https://www.youtube.com/iframe_api";
let loading: Promise<YouTubeNamespace> | null = null;

/** Loads the IFrame Player API once and resolves when it's ready. */
export function loadYouTubeApi(): Promise<YouTubeNamespace> {
  if (window.YT?.Player) {
    return Promise.resolve(window.YT);
  }
  loading ??= new Promise<YouTubeNamespace>((resolve, reject) => {
    window.onYouTubeIframeAPIReady = () => {
      if (window.YT) {
        resolve(window.YT);
      }
    };
    const script = document.createElement("script");
    script.src = API_URL;
    script.async = true;
    script.onerror = () => {
      loading = null;
      reject(new Error("Couldn't load the YouTube player."));
    };
    document.head.append(script);
  });
  return loading;
}

/**
 * Creates a player that never autoplays and never chains to another video. Captions stay off:
 * on songs they are lyrics, which MeloMind never displays (rule 15).
 */
export function createPlayer(
  api: YouTubeNamespace,
  element: HTMLElement,
  videoId: string,
  events: PlayerOptions["events"],
): YouTubePlayer {
  return new api.Player(element, {
    videoId,
    width: "100%",
    height: "100%",
    playerVars: {
      autoplay: 0,
      rel: 0,
      playsinline: 1,
      modestbranding: 1,
      iv_load_policy: 3,
      cc_load_policy: 0,
    },
    events,
  });
}

/** Turns captions off, if the viewer's YouTube settings had switched them on. */
export function hideCaptions(player: YouTubePlayer): void {
  player.unloadModule("captions");
  player.unloadModule("cc");
}
