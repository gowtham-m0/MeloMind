import type { ReactNode } from "react";

import { Button } from "./button";

interface ErrorBannerProps {
  error: Error;
  title?: string;
  onRetry?: () => void;
}

/** A calm, visible error with the backend's message and an optional retry. */
export function ErrorBanner({ error, title = "Something went wrong", onRetry }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-3 rounded-lg border-2 border-destructive bg-card p-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <p>
        <strong className="text-destructive">{title}.</strong> {error.message}
      </p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  children?: ReactNode;
}

/** What to show when a list has nothing in it yet, with what to do next. */
export function EmptyState({ title, children }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-lg border-2 border-dashed p-6">
      <p className="font-serif text-xl font-semibold">{title}</p>
      {children}
    </div>
  );
}

/** A quiet loading message, announced to screen readers. No spinners or flashing. */
export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <p role="status" aria-live="polite" className="text-muted-foreground">
      {label}
    </p>
  );
}
