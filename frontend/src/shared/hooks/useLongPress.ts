import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent, MouseEvent, PointerEvent } from "react";

/** Handlers to spread on the button, and how far the hold has got (0 to 1) for a visual cue. */
export interface LongPress {
  progress: number;
  handlers: {
    onPointerDown: (event: PointerEvent<HTMLElement>) => void;
    onPointerUp: () => void;
    onPointerLeave: () => void;
    onPointerCancel: () => void;
    onKeyDown: (event: KeyboardEvent<HTMLElement>) => void;
    onKeyUp: (event: KeyboardEvent<HTMLElement>) => void;
    onContextMenu: (event: MouseEvent<HTMLElement>) => void;
  };
}

/**
 * Calls `onLongPress` after the button has been held for `ms`, by pointer or by holding Enter
 * or Space. Letting go early cancels it, so a stray tap in Person mode does nothing.
 */
export function useLongPress(onLongPress: () => void, ms: number): LongPress {
  const [progress, setProgress] = useState(0);
  const frame = useRef<number | null>(null);
  const startedAt = useRef<number | null>(null);
  const callback = useRef(onLongPress);

  useEffect(() => {
    callback.current = onLongPress;
  }, [onLongPress]);

  const cancel = useCallback(() => {
    if (frame.current !== null) {
      cancelAnimationFrame(frame.current);
    }
    frame.current = null;
    startedAt.current = null;
    setProgress(0);
  }, []);

  const start = useCallback(() => {
    if (startedAt.current !== null) {
      return;
    }
    const began = performance.now();
    startedAt.current = began;
    const step = (now: number) => {
      if (startedAt.current !== began) {
        return;
      }
      const done = Math.min((now - began) / ms, 1);
      setProgress(done);
      if (done >= 1) {
        cancel();
        callback.current();
        return;
      }
      frame.current = requestAnimationFrame(step);
    };
    frame.current = requestAnimationFrame(step);
  }, [ms, cancel]);

  useEffect(() => cancel, [cancel]);

  return {
    progress,
    handlers: {
      onPointerDown: (event) => {
        start();
        // Keep receiving this pointer's events if the finger slides a little. Capture can fail
        // for a pointer the browser no longer tracks; the hold works without it.
        try {
          event.currentTarget.setPointerCapture(event.pointerId);
        } catch {
          // Nothing to do: pointerleave then ends the hold instead.
        }
      },
      onPointerUp: cancel,
      onPointerLeave: cancel,
      onPointerCancel: cancel,
      onKeyDown: (event) => {
        if ((event.key === "Enter" || event.key === " ") && !event.repeat) {
          event.preventDefault();
          start();
        }
      },
      onKeyUp: (event) => {
        if (event.key === "Enter" || event.key === " ") {
          cancel();
        }
      },
      onContextMenu: (event) => event.preventDefault(),
    },
  };
}
