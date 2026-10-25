import { useMutation } from "@tanstack/react-query";
import { cn } from "cn";
import { Lock, Mic, Square } from "lucide-react";
import { useId, useState, type RefObject } from "react";

import { transcribe, type JournalEntry } from "@/shared/api/journal";
import { Button } from "@/shared/ui/button";
import { ToggleChip } from "@/shared/ui/chip";

import { useCreateEntry } from "./hooks";
import { MAX_SECONDS, useRecorder } from "./useRecorder";

const MOODS = ["Chill", "Happy", "Focused", "Nostalgic", "Melancholy", "Energetic"];
const TEXT_MAX = 5000;

function today(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function clock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

interface ComposerProps {
  profileId: string;
  onSaved: (entry: JournalEntry) => void;
  textRef?: RefObject<HTMLTextAreaElement | null>;
}

/**
 * Write or speak today's entry. A voice note is transcribed, then lands in the text area to edit
 * before saving; the audio is never kept.
 */
export function Composer({ profileId, onSaved, textRef }: ComposerProps) {
  const textId = useId();
  const [text, setText] = useState("");
  const [date, setDate] = useState(today);
  const [mood, setMood] = useState<string | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const create = useCreateEntry(profileId);

  const listen = useMutation({
    mutationFn: (audio: Blob) => transcribe(profileId, audio),
    onSuccess: ({ text: heard }) => {
      setVoiceError(null);
      setText((current) => (current.trim() ? `${current.trim()} ${heard}` : heard));
      textRef?.current?.focus();
    },
    onError: () => setVoiceError("Couldn't hear that. Try again or type it."),
  });
  const recorder = useRecorder((audio) => listen.mutate(audio));
  const recording = recorder.state === "recording";

  const micMessage =
    recorder.state === "denied"
      ? "Allow the microphone to speak an entry, or type it."
      : recorder.state === "unsupported"
        ? "This browser can't record here. Type your entry instead."
        : voiceError;

  function save() {
    const body = text.trim();
    if (!body) {
      return;
    }
    create.mutate(
      { text: body, date, mood: mood?.toLowerCase() ?? null },
      {
        onSuccess: (entry) => {
          setText("");
          setMood(null);
          setDate(today());
          onSaved(entry);
        },
      },
    );
  }

  return (
    <section
      aria-labelledby="composer-title"
      className="rounded-2xl border border-hairline bg-surface p-4 shadow-soft md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="composer-title" className="text-[22px] font-semibold">
          What's on your mind?
        </h2>
        <label className="flex items-center gap-2 text-sm text-muted">
          <span className="sr-only">Entry date</span>
          <input
            type="date"
            value={date}
            max={today()}
            onChange={(event) => setDate(event.target.value || today())}
            className="h-10 rounded-lg border border-line bg-surface px-3 text-[15px] text-ink"
          />
        </label>
      </div>

      <div className="mt-4 flex gap-3">
        <label htmlFor={textId} className="sr-only">
          Your entry
        </label>
        <textarea
          id={textId}
          ref={textRef}
          value={text}
          maxLength={TEXT_MAX}
          onChange={(event) => setText(event.target.value)}
          rows={4}
          placeholder="Rewatched Interstellar tonight, then had Glass Animals on repeat…"
          className="min-h-32 w-full resize-y rounded-xl border border-transparent bg-surface-2 p-4 text-base leading-relaxed text-ink placeholder:text-muted focus:border-primary focus:bg-surface"
        />
        <div className="flex shrink-0 flex-col items-center gap-2">
          <button
            type="button"
            onClick={() => (recording ? recorder.stop() : void recorder.start())}
            disabled={listen.isPending || recorder.state === "asking"}
            aria-label={recording ? "Stop recording" : "Speak your entry"}
            aria-pressed={recording}
            className={cn(
              "relative grid size-16 place-items-center rounded-full transition-[background-color,transform] duration-200 ease-(--ease-out) active:scale-95 disabled:opacity-50",
              recording ? "bg-film text-white" : "bg-primary text-ink hover:bg-primary-hover",
            )}
          >
            {recording && (
              <span
                aria-hidden
                className="absolute inset-0 rounded-full bg-film/30 transition-transform duration-100"
                style={{ transform: `scale(${1 + recorder.level * 0.45})` }}
              />
            )}
            <span className="relative">
              {recording ? <Square className="size-5 fill-current" /> : <Mic className="size-6" />}
            </span>
          </button>
          <span className="tabular text-xs font-semibold text-muted" aria-live="polite">
            {recording
              ? `${clock(recorder.seconds)} / ${clock(MAX_SECONDS)}`
              : listen.isPending
                ? "Listening…"
                : "Speak"}
          </span>
        </div>
      </div>
      {micMessage && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {micMessage}
        </p>
      )}

      <div role="group" aria-label="Mood" className="mt-4 flex flex-wrap gap-2">
        {MOODS.map((option) => (
          <ToggleChip
            key={option}
            selected={mood === option}
            onClick={() => setMood(mood === option ? null : option)}
          >
            {option}
          </ToggleChip>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <p className="flex flex-1 items-center gap-2 text-sm text-muted">
          <Lock className="size-4 shrink-0" aria-hidden />
          Your journal is private. It's never shared.
        </p>
        {create.isError && (
          <p role="alert" className="text-sm text-danger">
            {create.error.message}
          </p>
        )}
        <Button onClick={save} disabled={!text.trim() || create.isPending || recording}>
          {create.isPending ? "Saving…" : "Save entry"}
        </Button>
      </div>
    </section>
  );
}
