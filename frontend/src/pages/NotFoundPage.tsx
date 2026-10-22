import { Link } from "react-router";

import { Button } from "@/shared/ui/button";

/** Shown for any URL that matches no route. */
export function NotFoundPage() {
  return (
    <section aria-labelledby="page-title" className="space-y-4">
      <h1 id="page-title" className="text-3xl font-semibold">
        Page not found
      </h1>
      <Button asChild variant="outline">
        <Link to="/">Go to the home page</Link>
      </Button>
    </section>
  );
}
