import { useParams } from "react-router";

import { FeedView } from "@/features/feed/FeedView";

/** The home feed for the profile in the URL. */
export function HomePage() {
  const { profileId = "" } = useParams();
  return <FeedView profileId={profileId} />;
}
