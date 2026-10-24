import { Link } from "react-router";

import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/states";

/** An unknown address. */
export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-xl p-6 pt-20">
      <EmptyState
        title="This page wandered off"
        action={
          <Button asChild>
            <Link to="/">Back to MeloMind</Link>
          </Button>
        }
      >
        The link may be old, or the profile may belong to someone else.
      </EmptyState>
    </div>
  );
}
