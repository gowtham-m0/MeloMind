import { useId, useState } from "react";
import { cn } from "cn";

import { COMMON_LANGUAGES, COUNTRIES } from "@/shared/data/countries";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

import type { BasicsErrors } from "./validation";

const selectClass =
  "h-12 w-full rounded-md border-2 border-input bg-card px-3 text-lg text-foreground";

function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) {
    return null;
  }
  return (
    <p id={id} className="font-bold text-destructive">
      {message}
    </p>
  );
}

interface BasicsFieldsProps {
  displayName: string;
  birthYear: string;
  errors: BasicsErrors;
  onDisplayNameChange: (value: string) => void;
  onBirthYearChange: (value: string) => void;
}

/** The two required fields: the name they're called by, and their birth year. */
export function BasicsFields(props: BasicsFieldsProps) {
  const id = useId();
  const { errors } = props;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-name`}>Their name</Label>
        <Input
          id={`${id}-name`}
          autoComplete="off"
          value={props.displayName}
          onChange={(event) => props.onDisplayNameChange(event.target.value)}
          aria-invalid={Boolean(errors.displayName)}
          aria-describedby={errors.displayName ? `${id}-name-error` : undefined}
          maxLength={60}
        />
        <FieldError id={`${id}-name-error`} message={errors.displayName} />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-year`}>Year they were born</Label>
        <Input
          id={`${id}-year`}
          inputMode="numeric"
          autoComplete="off"
          placeholder="For example, 1948"
          className="max-w-48"
          value={props.birthYear}
          onChange={(event) => props.onBirthYearChange(event.target.value.replace(/\D/g, ""))}
          aria-invalid={Boolean(errors.birthYear)}
          aria-describedby={errors.birthYear ? `${id}-year-error` : undefined}
          maxLength={4}
        />
        <FieldError id={`${id}-year-error`} message={errors.birthYear} />
      </div>
    </div>
  );
}

interface PlaceFieldsProps {
  countryCode: string;
  town: string;
  onCountryChange: (value: string) => void;
  onTownChange: (value: string) => void;
}

/** Where they grew up: a country, and a town if known. */
export function PlaceFields(props: PlaceFieldsProps) {
  const id = useId();

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-country`}>Country</Label>
        <select
          id={`${id}-country`}
          className={selectClass}
          value={props.countryCode}
          onChange={(event) => props.onCountryChange(event.target.value)}
        >
          <option value="">Not sure</option>
          {COUNTRIES.map((country) => (
            <option key={country.code} value={country.code}>
              {country.name}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-town`}>Town or city (optional)</Label>
        <Input
          id={`${id}-town`}
          autoComplete="off"
          placeholder="For example, Chicago"
          value={props.town}
          onChange={(event) => props.onTownChange(event.target.value)}
          maxLength={100}
        />
      </div>
    </div>
  );
}

interface LanguagesFieldProps {
  value: string[];
  onChange: (value: string[]) => void;
}

/** Languages they enjoyed music or films in: one-tap choices, plus any other typed in. */
export function LanguagesField({ value, onChange }: LanguagesFieldProps) {
  const id = useId();
  const [other, setOther] = useState("");
  const choices = [...COMMON_LANGUAGES, ...value.filter((l) => !COMMON_LANGUAGES.includes(l))];

  function toggle(language: string) {
    onChange(value.includes(language) ? value.filter((l) => l !== language) : [...value, language]);
  }

  function addOther() {
    const language = other.trim();
    if (language && !value.includes(language) && value.length < 10) {
      onChange([...value, language]);
    }
    setOther("");
  }

  return (
    <fieldset className="flex flex-col gap-4">
      <legend className="mb-2 text-lg font-bold">Languages</legend>
      <div className="flex flex-wrap gap-2">
        {choices.map((language) => {
          const selected = value.includes(language);
          return (
            <button
              key={language}
              type="button"
              aria-pressed={selected}
              onClick={() => toggle(language)}
              className={cn(
                "min-h-11 rounded-full border-2 px-4 text-lg",
                selected
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-input bg-card hover:bg-accent",
              )}
            >
              {language}
            </button>
          );
        })}
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-other`}>Another language</Label>
        <div className="flex gap-2">
          <Input
            id={`${id}-other`}
            autoComplete="off"
            value={other}
            maxLength={100}
            onChange={(event) => setOther(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                addOther();
              }
            }}
          />
          <Button type="button" variant="outline" onClick={addOther}>
            Add
          </Button>
        </div>
      </div>
    </fieldset>
  );
}
