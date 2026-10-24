import { cn } from "cn";
import { RotateCw } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "./button";
import { LogoMark } from "./logo";

/** A shimmering placeholder block. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn(
        "animate-pulse rounded-[10px] bg-[linear-gradient(100deg,var(--surface-2)_30%,var(--surface-3)_50%,var(--surface-2)_70%)]",
        className,
      )}
    />
  );
}

interface MessageProps {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}

/** Nothing here yet: says why, and what to do next. */
export function EmptyState({ title, children, action, className }: MessageProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-start gap-3 rounded-2xl border border-dashed border-line bg-surface-2/60 p-6",
        className,
      )}
    >
      <LogoMark className="size-9 opacity-80" />
      <h3 className="text-xl font-semibold">{title}</h3>
      {children && <p className="max-w-prose text-body">{children}</p>}
      {action}
    </div>
  );
}

interface ErrorProps {
  title?: string;
  error: unknown;
  onRetry?: () => void;
  className?: string;
}

/** Something broke: names the problem and offers the way back. */
export function ErrorState({ title = "That didn't load", error, onRetry, className }: ErrorProps) {
  const detail = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-start gap-3 rounded-2xl border border-film/30 bg-film/6 p-6",
        className,
      )}
    >
      <h3 className="text-xl font-semibold">{title}</h3>
      <p className="max-w-prose text-body">{detail}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          <RotateCw /> Try again
        </Button>
      )}
    </div>
  );
}
