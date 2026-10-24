import { NewProfileForm } from "@/features/profiles/NewProfileForm";
import { RequireSession } from "@/features/session/RequireSession";
import { Logo } from "@/shared/ui/logo";

/** A new profile: a name and a country, then the first feed builds. */
export function NewProfilePage() {
  return (
    <RequireSession>
      <div className="min-h-dvh bg-surface">
        <header className="mx-auto max-w-3xl px-5 py-5 md:px-8">
          <Logo />
        </header>
        <main className="mx-auto flex max-w-3xl flex-col gap-8 px-5 pt-8 pb-16 md:px-8">
          <div>
            <h1 className="text-[40px] leading-tight font-semibold md:text-[52px]">
              Let's get <span className="text-primary">you</span> started
            </h1>
            <p className="mt-2 max-w-[52ch] text-lg text-body">
              Two quick questions. Then search for a few favourites and watch the feed bend toward
              you.
            </p>
          </div>
          <NewProfileForm />
        </main>
      </div>
    </RequireSession>
  );
}
