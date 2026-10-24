import { cn } from "cn";

/** Where the user is in onboarding: filled dots for steps done, the current one wider. */
export function ProgressDots({ step, total }: { step: number; total: number }) {
  return (
    <div
      role="img"
      aria-label={`Step ${step + 1} of ${total}`}
      className="flex items-center gap-1.5"
    >
      {Array.from({ length: total }, (_, index) => (
        <span
          key={index}
          aria-hidden
          className={cn(
            "h-1.5 rounded-full transition-[width,background-color] duration-300 ease-(--ease-out)",
            index === step ? "w-6 bg-primary" : index < step ? "w-1.5 bg-ink" : "w-1.5 bg-line",
          )}
        />
      ))}
    </div>
  );
}
