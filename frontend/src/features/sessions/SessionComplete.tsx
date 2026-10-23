import { Link } from "react-router";

import { buttonVariants } from "@/shared/ui/button";

interface SessionCompleteProps {
  profileId: string;
  firstName: string;
}

/** The end of a session, with the next step: plan the next one. */
export function SessionComplete({ profileId, firstName }: SessionCompleteProps) {
  return (
    <section aria-labelledby="complete-title" className="flex flex-col gap-4">
      <h1 id="complete-title" className="text-3xl font-semibold">
        Session complete
      </h1>
      <p className="max-w-prose">
        Thank you. Your reactions shape what the agent picks for {firstName} next time, and the
        items you approved are on {firstName}'s Person-mode shelf.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link to={`/profiles/${profileId}/plan`} className={buttonVariants({ size: "lg" })}>
          Plan the next session
        </Link>
        <Link
          to={`/profiles/${profileId}/person`}
          className={buttonVariants({ variant: "outline", size: "lg" })}
        >
          Open Person mode
        </Link>
        <Link
          to={`/profiles/${profileId}`}
          className={buttonVariants({ variant: "ghost", size: "lg" })}
        >
          Back to the profile
        </Link>
      </div>
    </section>
  );
}
