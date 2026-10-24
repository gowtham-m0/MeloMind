import type { ReactNode } from "react";
import { Navigate } from "react-router";

import { Skeleton } from "@/shared/ui/states";

import { useSession } from "./useSession";

/** Shows its children to a signed-in user and sends everyone else to the landing page. */
export function RequireSession({ children }: { children: ReactNode }) {
  const { session, isLoading } = useSession();

  if (isLoading) {
    return (
      <div className="mx-auto flex max-w-5xl flex-col gap-4 p-6" aria-busy>
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (!session) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
