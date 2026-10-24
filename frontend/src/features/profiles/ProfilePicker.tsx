import { cn } from "cn";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";

import { DeleteProfile } from "@/features/settings/DeleteProfile";
import { Button } from "@/shared/ui/button";
import { ErrorState, Skeleton } from "@/shared/ui/states";

import { avatarColour, useProfiles } from "./hooks";

/**
 * Netflix-style profile picker: big avatars, then "Add profile". "Manage profiles" turns each
 * tile into a link to its settings, with a delete button in the corner.
 */
export function ProfilePicker() {
  const profiles = useProfiles();
  const [managing, setManaging] = useState(false);

  if (profiles.isPending) {
    return (
      <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4" aria-busy>
        {[0, 1, 2].map((index) => (
          <Skeleton key={index} className="aspect-square w-full rounded-2xl" />
        ))}
      </div>
    );
  }
  if (profiles.isError) {
    return <ErrorState error={profiles.error} onRetry={() => void profiles.refetch()} />;
  }

  return (
    <div className="flex flex-col gap-10">
      <ul className="grid grid-cols-2 gap-x-6 gap-y-8 sm:grid-cols-3 md:grid-cols-4">
        {profiles.data.map((profile, index) => (
          <li
            key={profile.id}
            className="rise-in relative"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <Link
              to={managing ? `/p/${profile.id}/settings` : `/p/${profile.id}`}
              aria-label={managing ? `Edit ${profile.display_name}` : undefined}
              className="group flex flex-col items-center gap-3 rounded-2xl p-2 text-center"
            >
              <span
                className={cn(
                  "lift relative grid aspect-square w-full place-items-center overflow-hidden rounded-2xl font-display text-6xl font-semibold text-ink/85",
                  avatarColour(profile.id),
                )}
              >
                {profile.display_name.slice(0, 1).toUpperCase()}
                {managing && (
                  <span className="fade-in absolute inset-0 grid place-items-center bg-ink/70 text-white">
                    <Pencil className="size-9" strokeWidth={1.75} />
                  </span>
                )}
              </span>
              <span className="flex flex-col">
                <span className="text-lg font-semibold text-ink">{profile.display_name}</span>
                <span className="text-sm text-muted">
                  {profile.favourites.length} favourite
                  {profile.favourites.length === 1 ? "" : "s"}
                  {profile.is_demo ? " · demo" : ""}
                </span>
              </span>
            </Link>
            {managing && (
              <DeleteProfile profile={profile}>
                <button
                  type="button"
                  aria-label={`Delete ${profile.display_name}`}
                  className="fade-in absolute top-0 right-0 grid size-11 place-items-center rounded-full border border-hairline bg-surface text-danger shadow-soft transition-transform duration-150 ease-(--ease-out) hover:scale-105 active:scale-95"
                >
                  <Trash2 className="size-[18px]" />
                </button>
              </DeleteProfile>
            )}
          </li>
        ))}
        {!managing && (
          <li>
            <Link
              to="/profiles/new"
              className="group flex flex-col items-center gap-3 rounded-2xl p-2 text-center"
            >
              <span className="grid aspect-square w-full place-items-center rounded-2xl border-2 border-dashed border-line text-muted transition-colors group-hover:border-primary group-hover:text-primary-ink">
                <Plus className="size-10" strokeWidth={1.5} />
              </span>
              <span className="text-lg font-semibold text-ink">Add profile</span>
            </Link>
          </li>
        )}
      </ul>
      {profiles.data.length > 0 && (
        <Button
          variant={managing ? "dark" : "secondary"}
          className="self-center"
          aria-pressed={managing}
          onClick={() => setManaging((on) => !on)}
        >
          {managing ? "Done" : "Manage profiles"}
        </Button>
      )}
    </div>
  );
}
