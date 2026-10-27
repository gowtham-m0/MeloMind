import { useParams } from "react-router";

import { MatchView } from "@/features/match/MatchView";

/** Taste match for the profile in the URL. */
export function MatchPage() {
  const { profileId = "" } = useParams();
  return <MatchView profileId={profileId} />;
}
