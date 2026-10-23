import * as React from "react";
import { cn } from "cn";

// Adapted from shadcn/ui: 48 px tall, 18 px text, a 2 px border at 3:1 contrast or more.
function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-12 w-full min-w-0 rounded-md border-2 border-input bg-card px-4 text-lg text-foreground placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
