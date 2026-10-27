import { Sparkles } from "lucide-react";
import { useState } from "react";

import { Button } from "@/shared/ui/button";
import { Sheet } from "@/shared/ui/sheet";

const EXAMPLES = [
  "Something like Interstellar but lighter",
  "A book for a long train ride",
  "90s indie I might have missed",
  "Shows to binge this weekend",
];
const MAX_LENGTH = 300;

interface AskComposerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  busy: boolean;
  onSubmit: (text: string) => void;
}

/** "Ask the agent": say what you're after in your own words, or tap an example. */
export function AskComposer({ open, onOpenChange, busy, onSubmit }: AskComposerProps) {
  const [text, setText] = useState("");
  const trimmed = text.trim();

  return (
    <Sheet open={open} onOpenChange={onOpenChange} title="Ask the agent">
      <form
        className="flex flex-col gap-5 p-6 pt-8"
        onSubmit={(event) => {
          event.preventDefault();
          if (trimmed && !busy) {
            onSubmit(trimmed);
            setText("");
          }
        }}
      >
        <div>
          <h2 className="text-[28px] leading-tight font-semibold">What are you after?</h2>
          <p className="mt-1.5 text-body">
            It turns your words into Qloo tags, adds your taste, and builds one extra row for the
            top of your feed.
          </p>
        </div>
        <label className="flex flex-col gap-2">
          <span className="sr-only">What are you after?</span>
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            maxLength={MAX_LENGTH}
            rows={3}
            placeholder="Something like Interstellar but lighter…"
            className="w-full resize-none rounded-xl border border-line bg-surface-2 p-4 text-base text-ink outline-none placeholder:text-muted focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/40"
          />
          <span className="self-end text-xs text-muted">
            {text.length}/{MAX_LENGTH}
          </span>
        </label>
        <ul aria-label="Examples" className="flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <li key={example}>
              <button
                type="button"
                onClick={() => setText(example)}
                className="inline-flex min-h-10 items-center rounded-full border border-line bg-surface px-4 text-left text-sm text-body transition-colors hover:border-[#c9c9c9] hover:text-ink"
              >
                {example}
              </button>
            </li>
          ))}
        </ul>
        <Button type="submit" size="lg" disabled={!trimmed || busy}>
          <Sparkles /> {busy ? "The agent is working…" : "Find it"}
        </Button>
      </form>
    </Sheet>
  );
}
