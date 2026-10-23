import type { ReactNode } from "react";

import { LoadingState } from "@/shared/ui/states";

import { TryDemoButton } from "./TryDemoButton";
import { useSession } from "./useSession";

/** Shows its children to a signed-in user, and the demo sign-in to everyone else. */
export function RequireSession({ children }: { children: ReactNode }) {
  const { session, isLoading } = useSession();

  if (isLoading) {
    return <LoadingState label="Checking your sign-in…" />;
  }
  if (!session) {
    return (
      <section aria-labelledby="sign-in-title" className="flex flex-col gap-4">
        <h1 id="sign-in-title" className="text-3xl font-semibold">
          Start with the demo
        </h1>
        <p className="max-w-prose">
          The demo gives you a private space with two sample profiles. Nothing you add is shared
          with anyone else.
        </p>
        <TryDemoButton />
      </section>
    );
  }
  return <>{children}</>;
}
