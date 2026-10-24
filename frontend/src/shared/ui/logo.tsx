import { cn } from "cn";

/** The MeloMind mark: an "M" drawn as a taste thread, its nodes in the four type colours. */
export function LogoMark({ className, onDark = false }: { className?: string; onDark?: boolean }) {
  return (
    <svg viewBox="0 0 180 180" aria-hidden className={cn("size-8", className)}>
      <polyline
        points="34,134 50,52 90,104 130,52 146,134"
        fill="none"
        stroke={onDark ? "#ffffff" : "var(--ink)"}
        strokeWidth="11"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="34" cy="134" r="13" fill="var(--book)" />
      <circle cx="50" cy="52" r="14" fill="var(--film)" />
      <circle cx="90" cy="104" r="17" fill="var(--music)" />
      <circle cx="130" cy="52" r="14" fill="var(--tv)" />
      <circle cx="146" cy="134" r="13" fill="var(--book)" />
    </svg>
  );
}

/** Mark plus wordmark, with the tagline when there's room. */
export function Logo({ withTagline = false }: { withTagline?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="flex flex-col leading-none">
        <span className="font-display text-[22px] font-semibold tracking-[-0.03em] text-ink">
          MeloMind
        </span>
        {withTagline && (
          <span className="mt-1 text-[11px] font-medium text-muted">
            Your personal culture companion
          </span>
        )}
      </span>
    </span>
  );
}
