import { useEffect, useRef, useState, type ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { FavouriteList } from "@/features/favourites/FavouriteList";
import { FavouritesEditor } from "@/features/favourites/FavouritesEditor";
import { withHometown } from "@/features/profiles/describe";
import { BasicsFields, LanguagesField, PlaceFields } from "@/features/profiles/fields";
import { useCreateProfile, useUpdateProfile } from "@/features/profiles/hooks";
import { ProfileLoader } from "@/features/profiles/ProfileLoader";
import { validateBasics, type BasicsErrors } from "@/features/profiles/validation";
import type { Profile } from "@/shared/api/profiles";
import { Button } from "@/shared/ui/button";
import { ErrorBanner } from "@/shared/ui/states";

const STEP_COUNT = 4;

/**
 * Onboarding, one question per screen. Step 1 creates the profile and later steps update it.
 * The profile ID and step live in the URL, so a refresh never loses progress.
 */
export function OnboardingStepper() {
  const [params, setParams] = useSearchParams();
  const profileId = params.get("id") ?? undefined;
  const requested = Number(params.get("step") ?? "1");
  const step = profileId && requested >= 1 && requested <= STEP_COUNT ? requested : 1;

  const goTo = (nextStep: number, id: string) =>
    setParams({ id, step: String(nextStep) }, { replace: false });

  if (!profileId) {
    return <BasicsStep onDone={(profile) => goTo(2, profile.id)} />;
  }

  return (
    <ProfileLoader id={profileId}>
      {(profile) => {
        switch (step) {
          case 1:
            return (
              <BasicsStep key={profile.id} profile={profile} onDone={() => goTo(2, profile.id)} />
            );
          case 2:
            return (
              <PlaceStep key={profile.id} profile={profile} onNext={() => goTo(3, profile.id)} />
            );
          case 3:
            return (
              <LanguagesStep
                key={profile.id}
                profile={profile}
                onBack={() => goTo(2, profile.id)}
                onNext={() => goTo(4, profile.id)}
              />
            );
          default:
            return <FavouritesStep profile={profile} onBack={() => goTo(3, profile.id)} />;
        }
      }}
    </ProfileLoader>
  );
}

interface StepFrameProps {
  step: number;
  title: string;
  intro?: string;
  children: ReactNode;
}

function StepFrame({ step, title, intro, children }: StepFrameProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, [step]);

  return (
    <section aria-labelledby="step-title" className="flex max-w-2xl flex-col gap-6">
      <p className="font-bold tracking-wide text-muted-foreground uppercase">
        Step {step} of {STEP_COUNT}
      </p>
      <div className="flex flex-col gap-2">
        <h1
          id="step-title"
          ref={headingRef}
          tabIndex={-1}
          className="text-3xl font-semibold focus-visible:outline-none"
        >
          {title}
        </h1>
        {intro && <p>{intro}</p>}
      </div>
      {children}
    </section>
  );
}

function BasicsStep({
  profile,
  onDone,
}: {
  profile?: Profile;
  onDone: (profile: Profile) => void;
}) {
  const create = useCreateProfile();
  const update = useUpdateProfile(profile?.id ?? "");
  const mutation = profile ? update : create;
  const [displayName, setDisplayName] = useState(profile?.display_name ?? "");
  const [birthYear, setBirthYear] = useState(profile ? String(profile.birth_year) : "");
  const [errors, setErrors] = useState<BasicsErrors>({});

  return (
    <StepFrame
      step={1}
      title="Who is this for?"
      intro="A birth year is enough to start. You can add more any time."
    >
      <form
        noValidate
        className="flex flex-col gap-6"
        onSubmit={(event) => {
          event.preventDefault();
          const found = validateBasics(displayName, birthYear);
          setErrors(found);
          if (Object.keys(found).length > 0) {
            return;
          }
          const body = { display_name: displayName.trim(), birth_year: Number(birthYear) };
          mutation.mutate(body, { onSuccess: onDone });
        }}
      >
        <BasicsFields
          displayName={displayName}
          birthYear={birthYear}
          errors={errors}
          onDisplayNameChange={setDisplayName}
          onBirthYearChange={setBirthYear}
        />
        {mutation.isError && <ErrorBanner error={mutation.error} title="Couldn't save that" />}
        <Button type="submit" size="lg" className="self-start" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Continue"}
        </Button>
      </form>
    </StepFrame>
  );
}

interface StepProps {
  profile: Profile;
  onNext: () => void;
}

function PlaceStep({ profile, onNext }: StepProps) {
  const update = useUpdateProfile(profile.id);
  const [countryCode, setCountryCode] = useState(profile.country_code ?? "");
  const [town, setTown] = useState(profile.places_lived[0] ?? "");

  return (
    <StepFrame
      step={2}
      title={`Where did ${profile.display_name} grow up?`}
      intro="This helps find the songs and films that were popular there."
    >
      <form
        className="flex flex-col gap-6"
        onSubmit={(event) => {
          event.preventDefault();
          update.mutate(
            {
              country_code: countryCode || null,
              places_lived: withHometown(profile.places_lived, town),
            },
            { onSuccess: onNext },
          );
        }}
      >
        <PlaceFields
          countryCode={countryCode}
          town={town}
          onCountryChange={setCountryCode}
          onTownChange={setTown}
        />
        {update.isError && <ErrorBanner error={update.error} title="Couldn't save that" />}
        <StepActions saving={update.isPending} onSkip={onNext} />
      </form>
    </StepFrame>
  );
}

function LanguagesStep({ profile, onNext, onBack }: StepProps & { onBack: () => void }) {
  const update = useUpdateProfile(profile.id);
  const [languages, setLanguages] = useState(profile.languages);

  return (
    <StepFrame
      step={3}
      title="Which languages did they enjoy music or films in?"
      intro="Choose any that fit."
    >
      <form
        className="flex flex-col gap-6"
        onSubmit={(event) => {
          event.preventDefault();
          update.mutate({ languages }, { onSuccess: onNext });
        }}
      >
        <LanguagesField value={languages} onChange={setLanguages} />
        {update.isError && <ErrorBanner error={update.error} title="Couldn't save that" />}
        <StepActions saving={update.isPending} onSkip={onNext} onBack={onBack} />
      </form>
    </StepFrame>
  );
}

function FavouritesStep({ profile, onBack }: { profile: Profile; onBack: () => void }) {
  const navigate = useNavigate();
  const done = () => void navigate(`/profiles/${profile.id}`);

  return (
    <StepFrame
      step={4}
      title={`What did ${profile.display_name} love when they were young?`}
      intro="Singers, songs, films, TV shows or books. Even one helps."
    >
      <FavouritesEditor profileId={profile.id} />
      <div className="flex flex-col gap-3">
        <h2 className="text-2xl font-semibold">Saved so far</h2>
        <FavouriteList profileId={profile.id} favourites={profile.favourites} />
      </div>
      <div className="flex flex-wrap gap-3">
        <Button size="lg" onClick={done}>
          {profile.favourites.length > 0 ? "Finish" : "Not sure, skip"}
        </Button>
        <Button variant="outline" size="lg" onClick={onBack}>
          Back
        </Button>
      </div>
    </StepFrame>
  );
}

interface StepActionsProps {
  saving: boolean;
  onSkip: () => void;
  onBack?: () => void;
}

function StepActions({ saving, onSkip, onBack }: StepActionsProps) {
  return (
    <div className="flex flex-wrap gap-3">
      <Button type="submit" size="lg" disabled={saving}>
        {saving ? "Saving…" : "Continue"}
      </Button>
      <Button type="button" variant="outline" size="lg" onClick={onSkip} disabled={saving}>
        Not sure, skip
      </Button>
      {onBack && (
        <Button type="button" variant="ghost" size="lg" onClick={onBack} disabled={saving}>
          Back
        </Button>
      )}
    </div>
  );
}
