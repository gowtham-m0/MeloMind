import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, Mail, MailCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import { continueWithEmail, continueWithGoogle, type AuthIntent } from "@/features/session/auth";
import { useAccount } from "@/features/session/useAccount";
import { Button } from "@/shared/ui/button";
import { Logo } from "@/shared/ui/logo";

/** Google's "G", in its own colours: the one place a brand colour is allowed. */
function GoogleMark() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden className="size-[18px]">
      <path
        fill="#EA4335"
        d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z"
      />
      <path
        fill="#4285F4"
        d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.6 5.9c4.4-4.1 7-10.1 7-17.6z"
      />
      <path
        fill="#FBBC05"
        d="M10.5 28.7a14.5 14.5 0 0 1 0-9.4l-7.9-6.1a24 24 0 0 0 0 21.6l7.9-6.1z"
      />
      <path
        fill="#34A853"
        d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.6-5.9c-2.1 1.4-4.9 2.3-8.3 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z"
      />
    </svg>
  );
}

/**
 * Real sign-in with Google or an emailed link. A guest from "Try the demo" gets the same page as
 * "Save your profiles": the new login is attached to the guest, so nothing they made is lost.
 */
export function SignInPage() {
  const { isGuest, isSignedIn, isLoading } = useAccount();
  const intent: AuthIntent = isGuest ? "save" : "signin";
  const [email, setEmail] = useState("");
  const google = useMutation({ mutationFn: () => continueWithGoogle(intent) });
  const emailLink = useMutation({ mutationFn: () => continueWithEmail(intent, email.trim()) });
  const error = google.error ?? emailLink.error;
  const backTo = isSignedIn ? "/profiles" : "/";

  function submit(event: FormEvent) {
    event.preventDefault();
    if (email.trim()) {
      emailLink.mutate();
    }
  }

  return (
    <div className="min-h-dvh bg-surface">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 md:px-8">
        <Link to="/" aria-label="MeloMind home">
          <Logo />
        </Link>
        <Button asChild variant="ghost" size="sm">
          <Link to={backTo}>
            <ArrowLeft /> Back
          </Link>
        </Button>
      </header>

      <main className="mx-auto flex max-w-md flex-col gap-7 px-5 pt-10 pb-20 md:pt-16">
        {emailLink.isSuccess ? (
          <section aria-live="polite" className="rise-in flex flex-col gap-4">
            <span className="grid size-12 place-items-center rounded-full bg-primary-tint">
              <MailCheck className="size-6 text-primary-ink" />
            </span>
            <h1 className="text-[34px] leading-[1.1] font-semibold">Check your email</h1>
            <p className="text-lg text-body">
              We sent a link to <strong className="text-ink">{email.trim()}</strong>. Open it on
              this device and you're in.
            </p>
            <Button variant="secondary" onClick={() => emailLink.reset()} className="self-start">
              Use a different email
            </Button>
          </section>
        ) : (
          <>
            <header className="flex flex-col gap-3">
              <h1 className="text-[34px] leading-[1.1] font-semibold md:text-[44px]">
                {isGuest ? "Keep your profiles" : "Welcome back"}
              </h1>
              <p className="text-lg text-body">
                {isGuest
                  ? "Add a sign-in to what you've built so far. Your profiles, likes and journal come with you to any device."
                  : "Sign in to get your profiles and feed on this device."}
              </p>
            </header>

            <div className="flex flex-col gap-5">
              <Button
                size="lg"
                variant="secondary"
                onClick={() => google.mutate()}
                disabled={google.isPending || isLoading}
                className="w-full"
              >
                <GoogleMark /> {google.isPending ? "Opening Google…" : "Continue with Google"}
              </Button>

              <div className="flex items-center gap-3 text-sm text-muted" aria-hidden>
                <span className="h-px flex-1 bg-line" /> or <span className="h-px flex-1 bg-line" />
              </div>

              <form onSubmit={submit} className="flex flex-col gap-3">
                <label htmlFor="email" className="text-sm font-semibold text-ink">
                  Email me a link
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  className="h-12 w-full rounded-[10px] bg-surface-2 px-4 text-base text-ink outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-primary/50"
                />
                <Button
                  type="submit"
                  size="lg"
                  disabled={emailLink.isPending || isLoading || email.trim().length === 0}
                  className="w-full"
                >
                  <Mail /> {emailLink.isPending ? "Sending…" : "Send the link"}
                </Button>
              </form>

              {error && (
                <p role="alert" className="text-danger">
                  {error.message}
                </p>
              )}
            </div>

            <p className="text-sm text-muted">
              No password to remember. We use your email only to sign you in.
            </p>
          </>
        )}
      </main>
    </div>
  );
}
