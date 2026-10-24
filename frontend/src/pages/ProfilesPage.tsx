import { ProfilePicker } from "@/features/profiles/ProfilePicker";
import { RequireSession } from "@/features/session/RequireSession";
import { Logo } from "@/shared/ui/logo";

/** "Who's exploring?": the Netflix-style profile picker. */
export function ProfilesPage() {
  return (
    <RequireSession>
      <div className="min-h-dvh bg-surface">
        <header className="mx-auto max-w-4xl px-5 py-5 md:px-8">
          <Logo />
        </header>
        <main className="mx-auto flex max-w-4xl flex-col gap-10 px-5 pt-8 pb-16 md:px-8">
          <div>
            <h1 className="text-[40px] leading-tight font-semibold md:text-[52px]">
              Who's exploring?
            </h1>
            <p className="mt-2 text-lg text-body">
              Each profile has its own taste, feed and saves.
            </p>
          </div>
          <ProfilePicker />
        </main>
      </div>
    </RequireSession>
  );
}
