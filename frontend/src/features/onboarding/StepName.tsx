import { ArrowRight } from "lucide-react";
import { useId, type FormEvent } from "react";

import { Button } from "@/shared/ui/button";

const NAME_MAX = 60;

interface StepNameProps {
  name: string;
  onChange: (name: string) => void;
  onNext: () => void;
}

/** Step 1: what should we call you. The only required answer in onboarding. */
export function StepName({ name, onChange, onNext }: StepNameProps) {
  const id = useId();
  const ready = name.trim().length > 0;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (ready) {
      onNext();
    }
  }

  return (
    <form onSubmit={submit} className="flex max-w-md flex-col gap-6">
      <div>
        <h1 className="text-[40px] leading-tight font-semibold md:text-[52px]">
          Let's get <span className="text-primary">you</span> started
        </h1>
        <p className="mt-2 max-w-[48ch] text-lg text-body">
          A few questions about your taste, and your home screen is built around you.
        </p>
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor={id} className="font-semibold text-ink">
          What should we call you?
        </label>
        <input
          id={id}
          value={name}
          maxLength={NAME_MAX}
          autoFocus
          autoComplete="given-name"
          onChange={(event) => onChange(event.target.value)}
          placeholder="Your first name"
          className="h-12 rounded-[10px] border border-line bg-surface px-4 text-base text-ink placeholder:text-muted focus:border-primary"
        />
      </div>
      <Button type="submit" size="lg" disabled={!ready} className="self-start">
        Continue <ArrowRight />
      </Button>
    </form>
  );
}
