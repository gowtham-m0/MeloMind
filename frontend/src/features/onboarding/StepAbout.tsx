import { ArrowRight } from "lucide-react";
import { useId, type FormEvent } from "react";

import { COUNTRIES } from "@/shared/data/countries";
import { Button } from "@/shared/ui/button";

import { MIN_BIRTH_YEAR, parseBirthYear, type About } from "./about";

interface StepAboutProps {
  about: About;
  busy: boolean;
  error: string | null;
  onChange: (about: About) => void;
  onNext: () => void;
}

/** Step 2: country and birth year. Both are optional and say what they're for. */
export function StepAbout({ about, busy, error, onChange, onNext }: StepAboutProps) {
  const countryId = useId();
  const yearId = useId();
  const yearOk = !about.birthYear.trim() || parseBirthYear(about.birthYear) !== null;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (yearOk) {
      onNext();
    }
  }

  return (
    <form onSubmit={submit} className="flex max-w-md flex-col gap-6">
      <div>
        <h1 className="text-[36px] leading-tight font-semibold md:text-[44px]">
          A little about <span className="text-primary">where</span> you are
        </h1>
        <p className="mt-2 max-w-[48ch] text-lg text-body">
          Both are optional. Skip either one and nothing breaks.
        </p>
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor={countryId} className="font-semibold text-ink">
          Where do you live?
        </label>
        <select
          id={countryId}
          value={about.country}
          onChange={(event) => onChange({ ...about, country: event.target.value })}
          className="h-12 rounded-[10px] border border-line bg-surface px-3 text-base text-ink focus:border-primary"
        >
          <option value="">Skip for now</option>
          {COUNTRIES.map((option) => (
            <option key={option.code} value={option.code}>
              {option.name}
            </option>
          ))}
        </select>
        <p className="text-sm text-muted">It powers “Popular in…” and the right streaming links.</p>
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor={yearId} className="font-semibold text-ink">
          What year were you born?
        </label>
        <input
          id={yearId}
          inputMode="numeric"
          maxLength={4}
          value={about.birthYear}
          onChange={(event) =>
            onChange({ ...about, birthYear: event.target.value.replace(/\D/g, "") })
          }
          placeholder="Not sure, skip"
          aria-invalid={!yearOk}
          aria-describedby={`${yearId}-hint`}
          className="h-12 rounded-[10px] border border-line bg-surface px-4 text-base text-ink placeholder:text-muted focus:border-primary aria-invalid:border-danger"
        />
        <p id={`${yearId}-hint`} className={yearOk ? "text-sm text-muted" : "text-sm text-danger"}>
          {yearOk
            ? "Only used for an optional “Throwback” row."
            : `Use a year from ${MIN_BIRTH_YEAR} to ${new Date().getFullYear()}.`}
        </p>
      </div>
      {error && (
        <p role="alert" className="text-danger">
          {error}
        </p>
      )}
      <Button type="submit" size="lg" disabled={!yearOk || busy} className="self-start">
        {busy ? "Saving…" : "Continue"} <ArrowRight />
      </Button>
    </form>
  );
}
