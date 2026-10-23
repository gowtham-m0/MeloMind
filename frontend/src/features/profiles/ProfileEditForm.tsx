import { useState } from "react";
import { useNavigate } from "react-router";

import type { Profile } from "@/shared/api/profiles";
import { Button } from "@/shared/ui/button";
import { ErrorBanner } from "@/shared/ui/states";

import { withHometown } from "./describe";
import { BasicsFields, LanguagesField, PlaceFields } from "./fields";
import { useDeleteProfile, useUpdateProfile } from "./hooks";
import { validateBasics, type BasicsErrors } from "./validation";

/** Every profile field on one page: the same questions as onboarding. */
export function ProfileEditForm({ profile }: { profile: Profile }) {
  const navigate = useNavigate();
  const update = useUpdateProfile(profile.id);
  const [displayName, setDisplayName] = useState(profile.display_name);
  const [birthYear, setBirthYear] = useState(String(profile.birth_year));
  const [countryCode, setCountryCode] = useState(profile.country_code ?? "");
  const [town, setTown] = useState(profile.places_lived[0] ?? "");
  const [languages, setLanguages] = useState(profile.languages);
  const [errors, setErrors] = useState<BasicsErrors>({});

  return (
    <div className="flex flex-col gap-10">
      <form
        noValidate
        className="flex flex-col gap-8"
        onSubmit={(event) => {
          event.preventDefault();
          const found = validateBasics(displayName, birthYear);
          setErrors(found);
          if (Object.keys(found).length > 0) {
            return;
          }
          update.mutate(
            {
              display_name: displayName.trim(),
              birth_year: Number(birthYear),
              country_code: countryCode || null,
              places_lived: withHometown(profile.places_lived, town),
              languages,
            },
            { onSuccess: () => void navigate(`/profiles/${profile.id}`) },
          );
        }}
      >
        <BasicsFields
          displayName={displayName}
          birthYear={birthYear}
          errors={errors}
          onDisplayNameChange={setDisplayName}
          onBirthYearChange={setBirthYear}
        />
        <PlaceFields
          countryCode={countryCode}
          town={town}
          onCountryChange={setCountryCode}
          onTownChange={setTown}
        />
        <LanguagesField value={languages} onChange={setLanguages} />
        {update.isError && <ErrorBanner error={update.error} title="Couldn't save the changes" />}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save changes"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => void navigate(`/profiles/${profile.id}`)}
          >
            Cancel
          </Button>
        </div>
      </form>
      <DeleteProfile profile={profile} />
    </div>
  );
}

function DeleteProfile({ profile }: { profile: Profile }) {
  const navigate = useNavigate();
  const remove = useDeleteProfile(profile.id);
  const [confirming, setConfirming] = useState(false);

  return (
    <section aria-labelledby="delete-title" className="flex flex-col gap-3 border-t-2 pt-6">
      <h2 id="delete-title" className="text-2xl font-semibold">
        Delete this profile
      </h2>
      <p>This deletes {profile.display_name}'s profile and favourites. It can't be undone.</p>
      {remove.isError && <ErrorBanner error={remove.error} title="Couldn't delete the profile" />}
      {confirming ? (
        <div className="flex flex-wrap gap-3">
          <Button
            variant="destructive"
            disabled={remove.isPending}
            onClick={() =>
              remove.mutate(undefined, { onSuccess: () => void navigate("/profiles") })
            }
          >
            Yes, delete {profile.display_name}
          </Button>
          <Button variant="outline" onClick={() => setConfirming(false)}>
            Keep it
          </Button>
        </div>
      ) : (
        <Button variant="outline" className="self-start" onClick={() => setConfirming(true)}>
          Delete profile…
        </Button>
      )}
    </section>
  );
}
