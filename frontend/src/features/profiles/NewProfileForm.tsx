import { ArrowRight } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { COUNTRIES } from "@/shared/data/countries";
import { Button } from "@/shared/ui/button";

import { useCreateProfile } from "./hooks";

const NAME_MAX = 60;

/** A new profile from a name and, optionally, a country. The full onboarding with favourites
 * and the taste quiz comes in the next pass; the first feed starts from popular picks. */
export function NewProfileForm() {
  const nameId = useId();
  const countryId = useId();
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const create = useCreateProfile();
  const navigate = useNavigate();
  const trimmed = name.trim();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!trimmed) {
      return;
    }
    const profile = await create.mutateAsync({
      display_name: trimmed,
      country_code: country || null,
    });
    await navigate(`/p/${profile.id}`);
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="flex max-w-md flex-col gap-6">
      <div className="flex flex-col gap-2">
        <label htmlFor={nameId} className="font-semibold text-ink">
          What should we call you?
        </label>
        <input
          id={nameId}
          value={name}
          maxLength={NAME_MAX}
          autoComplete="given-name"
          onChange={(event) => setName(event.target.value)}
          placeholder="Your first name"
          className="h-12 rounded-[10px] border border-line bg-surface px-4 text-base text-ink placeholder:text-muted focus:border-primary"
        />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor={countryId} className="font-semibold text-ink">
          Where do you live? <span className="font-normal text-muted">(optional)</span>
        </label>
        <select
          id={countryId}
          value={country}
          onChange={(event) => setCountry(event.target.value)}
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
      {create.isError && (
        <p role="alert" className="text-danger">
          {create.error.message}
        </p>
      )}
      <Button
        type="submit"
        size="lg"
        disabled={!trimmed || create.isPending}
        className="self-start"
      >
        {create.isPending ? "Creating…" : "Build my feed"} <ArrowRight />
      </Button>
    </form>
  );
}
