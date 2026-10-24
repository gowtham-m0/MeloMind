import { useState } from "react";
import { useNavigate } from "react-router";

import { Logo } from "@/shared/ui/logo";

import { useCreateProfile } from "../profiles/hooks";

import { ProgressDots } from "./ProgressDots";
import { parseBirthYear, type About } from "./about";
import { StepAbout } from "./StepAbout";
import { StepFavourites } from "./StepFavourites";
import { StepName } from "./StepName";
import { StepQuiz } from "./StepQuiz";

const STEPS = 4;

/** The browser's region as a country code, so the country question starts filled in. */
function guessCountry(): string {
  try {
    return new Intl.Locale(navigator.language).region ?? "";
  } catch {
    return "";
  }
}

/**
 * First-run onboarding, one question per screen: name, country and birth year, favourites, then
 * the this-or-that quiz. The profile is created when the second step is answered, so favourites
 * and quiz picks have somewhere to go. After the quiz, the home screen builds the first feed and
 * shows the agent's log.
 */
export function OnboardingFlow() {
  const navigate = useNavigate();
  const create = useCreateProfile();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [about, setAbout] = useState<About>({ country: guessCountry(), birthYear: "" });
  const [profileId, setProfileId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function createProfile() {
    setError(null);
    try {
      const profile = await create.mutateAsync({
        display_name: name.trim(),
        country_code: about.country || null,
        birth_year: parseBirthYear(about.birthYear),
      });
      setProfileId(profile.id);
      setStep(2);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Couldn't save that. Try again.");
    }
  }

  const finish = () => {
    if (profileId) {
      void navigate(`/p/${profileId}`);
    }
  };

  return (
    <div className="min-h-dvh bg-surface">
      <header className="mx-auto flex max-w-4xl items-center justify-between px-5 py-5 md:px-8">
        <Logo />
        <ProgressDots step={step} total={STEPS} />
      </header>
      <main className="mx-auto max-w-4xl px-5 pt-6 pb-10 md:px-8">
        <div key={step} className="rise-in">
          {step === 0 && <StepName name={name} onChange={setName} onNext={() => setStep(1)} />}
          {step === 1 && (
            <StepAbout
              about={about}
              busy={create.isPending}
              error={error}
              onChange={setAbout}
              onNext={() => void createProfile()}
            />
          )}
          {step === 2 && profileId && (
            <StepFavourites profileId={profileId} name={name.trim()} onNext={() => setStep(3)} />
          )}
          {step === 3 && profileId && <StepQuiz profileId={profileId} onDone={finish} />}
        </div>
      </main>
    </div>
  );
}
