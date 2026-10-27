import { Check } from "lucide-react";
import { useId, useState, type FormEvent } from "react";

import type { Profile } from "@/shared/api/profiles";
import { COUNTRIES } from "@/shared/data/countries";
import { Button } from "@/shared/ui/button";
import { useToast } from "@/shared/ui/toast";

import { MIN_BIRTH_YEAR, parseBirthYear } from "../onboarding/about";
import { useUpdateProfile } from "../profiles/hooks";

const NAME_MAX = 60;

const field =
  "h-12 w-full rounded-[10px] border border-line bg-surface px-4 text-base text-ink placeholder:text-muted focus:border-primary aria-invalid:border-danger";

/** Name, country and birth year. Country and birth year stay optional and say what they do. */
export function ProfileForm({ profile }: { profile: Profile }) {
  const nameId = useId();
  const countryId = useId();
  const yearId = useId();
  const toast = useToast();
  const update = useUpdateProfile(profile.id);
  const [name, setName] = useState(profile.display_name);
  const [country, setCountry] = useState(profile.country_code ?? "");
  const [birthYear, setBirthYear] = useState(profile.birth_year ? String(profile.birth_year) : "");

  const trimmed = name.trim();
  const yearOk = !birthYear.trim() || parseBirthYear(birthYear) !== null;
  const changed =
    trimmed !== profile.display_name ||
    country !== (profile.country_code ?? "") ||
    parseBirthYear(birthYear) !== (profile.birth_year ?? null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!trimmed || !yearOk || !changed) {
      return;
    }
    try {
      await update.mutateAsync({
        display_name: trimmed,
        country_code: country || null,
        birth_year: parseBirthYear(birthYear),
      });
    } catch {
      return; // The error shows under the form.
    }
    toast.show("Saved. Refresh your feed to see the change.");
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="flex max-w-md flex-col gap-5">
      <div className="flex flex-col gap-2">
        <label htmlFor={nameId} className="font-semibold text-ink">
          Name
        </label>
        <input
          id={nameId}
          value={name}
          maxLength={NAME_MAX}
          autoComplete="given-name"
          aria-invalid={!trimmed}
          onChange={(event) => setName(event.target.value)}
          className={field}
        />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor={countryId} className="font-semibold text-ink">
          Country
        </label>
        <select
          id={countryId}
          value={country}
          onChange={(event) => setCountry(event.target.value)}
          className={`${field} px-3`}
        >
          <option value="">Not set</option>
          {COUNTRIES.map((option) => (
            <option key={option.code} value={option.code}>
              {option.name}
            </option>
          ))}
        </select>
        <p className="text-sm text-muted">Powers “Popular in…” and the right streaming links.</p>
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor={yearId} className="font-semibold text-ink">
          Birth year
        </label>
        <input
          id={yearId}
          inputMode="numeric"
          maxLength={4}
          value={birthYear}
          placeholder="Not set"
          aria-invalid={!yearOk}
          aria-describedby={`${yearId}-hint`}
          onChange={(event) => setBirthYear(event.target.value.replace(/\D/g, ""))}
          className={field}
        />
        <p id={`${yearId}-hint`} className={yearOk ? "text-sm text-muted" : "text-sm text-danger"}>
          {yearOk
            ? "Only used for the “Throwback” row. Clear it to turn that row off."
            : `Use a year from ${MIN_BIRTH_YEAR} to ${new Date().getFullYear()}.`}
        </p>
      </div>
      {update.isError && (
        <p role="alert" className="text-danger">
          {update.error.message}
        </p>
      )}
      <Button
        type="submit"
        disabled={!trimmed || !yearOk || !changed || update.isPending}
        className="self-start"
      >
        <Check /> {update.isPending ? "Saving…" : "Save changes"}
      </Button>
    </form>
  );
}
