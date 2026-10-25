import { useCallback, useEffect, useRef, useState } from "react";

/** Two minutes, the backend's limit for a voice note. */
export const MAX_SECONDS = 120;
const MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

export type RecorderState = "idle" | "asking" | "recording" | "denied" | "unsupported";

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") {
    return undefined;
  }
  return MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
}

/**
 * Records a voice note with `MediaRecorder`: a live timer, a level from 0 to 1 for the meter,
 * and a hard stop at two minutes. The recording is handed to `onDone` and never kept here.
 */
export function useRecorder(onDone: (audio: Blob) => void) {
  const [state, setState] = useState<RecorderState>("idle");
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const cleanup = useRef<() => void>(() => undefined);
  const onDoneRef = useRef(onDone);

  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  useEffect(() => () => cleanup.current(), []);

  const stop = useCallback(() => {
    if (recorder.current?.state === "recording") {
      recorder.current.stop();
    }
  }, []);

  const start = useCallback(async () => {
    const mimeType = pickMimeType();
    if (!navigator.mediaDevices?.getUserMedia || mimeType === undefined) {
      setState("unsupported");
      return;
    }
    setState("asking");
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setState("denied");
      return;
    }

    const context = new AudioContext();
    const analyser = context.createAnalyser();
    analyser.fftSize = 512;
    context.createMediaStreamSource(stream).connect(analyser);
    const samples = new Uint8Array(analyser.fftSize);
    let frame = 0;
    const measure = () => {
      analyser.getByteTimeDomainData(samples);
      let sum = 0;
      for (const sample of samples) {
        const centred = (sample - 128) / 128;
        sum += centred * centred;
      }
      setLevel(Math.min(Math.sqrt(sum / samples.length) * 3, 1));
      frame = requestAnimationFrame(measure);
    };
    frame = requestAnimationFrame(measure);

    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setSeconds(elapsed);
      if (elapsed >= MAX_SECONDS) {
        stop();
      }
    }, 250);

    const chunks: Blob[] = [];
    const media = new MediaRecorder(stream, { mimeType });
    media.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };
    cleanup.current = () => {
      cancelAnimationFrame(frame);
      window.clearInterval(timer);
      stream.getTracks().forEach((track) => track.stop());
      void context.close().catch(() => undefined);
    };
    media.onstop = () => {
      cleanup.current();
      cleanup.current = () => undefined;
      recorder.current = null;
      setState("idle");
      setLevel(0);
      const audio = new Blob(chunks, { type: mimeType.split(";")[0] });
      if (audio.size > 0) {
        onDoneRef.current(audio);
      }
    };
    recorder.current = media;
    setSeconds(0);
    media.start(1000);
    setState("recording");
  }, [stop]);

  return { state, seconds, level, start, stop };
}
