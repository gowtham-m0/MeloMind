import { Link } from "react-router";

import { TryDemoButton } from "@/features/demo/TryDemoButton";
import { BackendStatus } from "@/features/health/BackendStatus";
import { buttonVariants } from "@/shared/ui/button";

/** Landing page: what MeloMind is, the demo sign-in, and whether the backend is reachable. */
export function HomePage() {
  return (
    <div className="flex flex-col gap-10">
      <section aria-labelledby="home-title" className="flex max-w-2xl flex-col gap-5">
        <h1 id="home-title" className="text-4xl font-semibold sm:text-5xl">
          Music and memories, shared at their pace
        </h1>
        <p>
          MeloMind helps families and caregivers prepare short sessions of songs, films, TV and
          books from a loved one's youth, with gentle prompts to talk about them.
        </p>
        <div className="flex flex-wrap items-start gap-3">
          <TryDemoButton />
          <Link to="/profiles" className={buttonVariants({ variant: "outline", size: "lg" })}>
            Your profiles
          </Link>
        </div>
      </section>
      <BackendStatus />
    </div>
  );
}
