import { Heart, Info, Sparkles, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/shared/ui/button";

const storageKey = (profileId: string) => `melomind:welcome:${profileId}`;

function wasDismissed(profileId: string): boolean {
  try {
    return window.localStorage.getItem(storageKey(profileId)) !== null;
  } catch {
    return false;
  }
}

const STEPS = [
  { icon: Heart, text: "Heart a pick. The agent learns from every tap." },
  { icon: Info, text: "Open any card and see exactly why it's here." },
  { icon: Sparkles, text: "Ask in your own words, or set a mood on the right." },
];

/** A one-time hello after the first feed: three things to try. Remembered per profile, in this
 * browser only. */
export function WelcomeTip({ profileId, onAsk }: { profileId: string; onAsk: () => void }) {
  const [hidden, setHidden] = useState(() => wasDismissed(profileId));
  if (hidden) {
    return null;
  }

  function dismiss() {
    setHidden(true);
    try {
      window.localStorage.setItem(storageKey(profileId), "1");
    } catch {
      // Private windows can refuse storage; the tip just comes back next visit.
    }
  }

  return (
    <section
      aria-labelledby="welcome-title"
      className="rise-in relative rounded-2xl border border-primary/40 bg-primary-tint/50 p-5 pr-14"
    >
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss the welcome tips"
        className="absolute top-3 right-3 grid size-10 place-items-center rounded-full text-body transition-colors hover:bg-white/70 hover:text-ink"
      >
        <X className="size-[18px]" />
      </button>
      <h2 id="welcome-title" className="text-lg font-semibold">
        Your feed is ready. Here's how to steer it.
      </h2>
      <ul className="mt-3 grid gap-2.5 md:grid-cols-3">
        {STEPS.map((step) => (
          <li key={step.text} className="flex items-start gap-3 text-[15px] text-body">
            <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-white text-primary-ink">
              <step.icon className="size-4" aria-hidden />
            </span>
            <span className="pt-1">{step.text}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          size="sm"
          onClick={() => {
            dismiss();
            onAsk();
          }}
        >
          <Sparkles /> Ask the agent
        </Button>
        <Button variant="ghost" size="sm" onClick={dismiss}>
          Got it
        </Button>
      </div>
    </section>
  );
}
