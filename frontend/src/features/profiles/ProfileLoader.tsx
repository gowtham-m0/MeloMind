import type { ReactNode } from "react";
import { Link } from "react-router";

import { ApiError } from "@/shared/api/client";
import type { Profile } from "@/shared/api/profiles";
import { buttonVariants } from "@/shared/ui/button";
import { EmptyState, ErrorBanner, LoadingState } from "@/shared/ui/states";

import { useProfile } from "./hooks";

interface ProfileLoaderProps {
  id: string | undefined;
  children: (profile: Profile) => ReactNode;
}

/** Loads one profile and renders its children with it, or a loading, missing or error state. */
export function ProfileLoader({ id, children }: ProfileLoaderProps) {
  const profile = useProfile(id);

  if (profile.isPending) {
    return <LoadingState label="Loading the profile…" />;
  }
  if (profile.isError) {
    if (profile.error instanceof ApiError && profile.error.status === 404) {
      return (
        <EmptyState title="We couldn't find that profile">
          <p>It may have been deleted, or it belongs to someone else.</p>
          <Link to="/profiles" className={buttonVariants({ variant: "outline" })}>
            Back to profiles
          </Link>
        </EmptyState>
      );
    }
    return (
      <ErrorBanner
        error={profile.error}
        title="Couldn't load the profile"
        onRetry={() => void profile.refetch()}
      />
    );
  }
  return <>{children(profile.data)}</>;
}
