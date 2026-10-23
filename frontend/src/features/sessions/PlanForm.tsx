import { cn } from "cn";
import { useState } from "react";
import { useNavigate } from "react-router";

import { Button } from "@/shared/ui/button";
import { ErrorBanner } from "@/shared/ui/states";

import { usePlanSession } from "./hooks";

const LENGTHS = [10, 20, 30] as const;
type Length = (typeof LENGTHS)[number];

interface PlanFormProps {
  profileId: string;
  firstName: string;
}

/** Choose a length and ask the agent to plan. The session page then shows its log. */
export function PlanForm({ profileId, firstName }: PlanFormProps) {
  const [minutes, setMinutes] = useState<Length>(20);
  const plan = usePlanSession(profileId);
  const navigate = useNavigate();

  const submit = () => {
    plan.mutate(
      { mode: "standard", target_minutes: minutes },
      { onSuccess: (session) => void navigate(`/sessions/${session.id}`) },
    );
  };

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <fieldset className="flex flex-col gap-3">
        <legend className="mb-2 text-xl font-semibold">How long should it be?</legend>
        <div className="flex flex-wrap gap-3">
          {LENGTHS.map((length) => (
            <label
              key={length}
              className={cn(
                "inline-flex min-h-14 cursor-pointer items-center gap-3 rounded-lg border-2 px-5 text-xl has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-ring",
                minutes === length ? "border-primary bg-secondary font-bold" : "bg-card",
              )}
            >
              <input
                type="radio"
                name="length"
                value={length}
                checked={minutes === length}
                onChange={() => setMinutes(length)}
                className="size-5 accent-primary"
              />
              {length} minutes
            </label>
          ))}
        </div>
      </fieldset>
      <p className="max-w-prose text-muted-foreground">
        The agent looks for music, films, TV and a book from {firstName}'s youth, then you review
        everything before anything is played.
      </p>
      {plan.isError && <ErrorBanner error={plan.error} title="Couldn't start planning" />}
      <Button type="submit" size="lg" className="self-start" disabled={plan.isPending}>
        {plan.isPending ? "Starting…" : "Plan today's session"}
      </Button>
    </form>
  );
}
