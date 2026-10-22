import { BackendStatus } from "@/features/health/BackendStatus";
import { PlaceholderPage } from "@/shared/ui/placeholder-page";

/** Landing page: what MeloMind is, and whether the backend is reachable. */
export function HomePage() {
  return (
    <PlaceholderPage title="MeloMind">
      <p>Personal music and memory sessions for families and caregivers.</p>
      <BackendStatus />
    </PlaceholderPage>
  );
}
