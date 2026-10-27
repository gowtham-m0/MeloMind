import { Link, useRouteError } from "react-router";

import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states";

/** What any route shows when its code fails to load or throws: a designed way back, not the
 * router's bare default. */
export function RouteErrorPage() {
  const error = useRouteError();

  return (
    <div className="mx-auto max-w-xl p-6 pt-20">
      <ErrorState
        title="Something went wrong on this page"
        error={error instanceof Error ? error : new Error("Reload the page, or head back home.")}
        onRetry={() => window.location.reload()}
      />
      <Button asChild variant="ghost" className="mt-4">
        <Link to="/">Back to MeloMind</Link>
      </Button>
    </div>
  );
}
