import { cn } from "cn";
import { useState } from "react";

import type { FeedbackResult, Reaction } from "@/shared/api/sessions";
import { Button } from "@/shared/ui/button";

import { REACTIONS } from "./labels";

interface ReactionButtonsProps {
  title: string;
  onReact: (reaction: Reaction) => Promise<FeedbackResult>;
  className?: string;
}

/**
 * How the person reacted, in the caregiver's words. Rejecting asks first, because a rejected
 * item never comes back. Upset hides the item until the caregiver reviews it.
 */
export function ReactionButtons({ title, onReact, className }: ReactionButtonsProps) {
  const [sent, setSent] = useState<Reaction | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);

  const send = async (reaction: Reaction) => {
    setConfirming(false);
    setPending(true);
    try {
      const result = await onReact(reaction);
      setSent(reaction);
      setMessage(result.effect);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Couldn't save the reaction.");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <p className="font-semibold">How did they react?</p>
      <div className="flex flex-wrap gap-2">
        {REACTIONS.map(({ value, label }) => (
          <Button
            key={value}
            variant={sent === value ? "default" : value === "rejected" ? "destructive" : "outline"}
            disabled={pending}
            aria-pressed={sent === value}
            onClick={() => (value === "rejected" ? setConfirming(true) : void send(value))}
          >
            {label}
          </Button>
        ))}
      </div>
      {confirming && (
        <div className="flex flex-col gap-3 rounded-lg border-2 border-destructive bg-card p-4">
          <p>
            Reject <strong>{title}</strong> for good? It won't be suggested again, anywhere.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variant="destructive" onClick={() => void send("rejected")}>
              Yes, reject it
            </Button>
            <Button variant="outline" onClick={() => setConfirming(false)}>
              Keep it
            </Button>
          </div>
        </div>
      )}
      <p role="status" aria-live="polite" className="min-h-7 text-muted-foreground">
        {message}
      </p>
    </div>
  );
}
