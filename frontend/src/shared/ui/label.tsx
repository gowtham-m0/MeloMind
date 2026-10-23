import * as React from "react";
import { cn } from "cn";

// Adapted from shadcn/ui as a plain label: bold 18 px text above its field.
function Label({ className, ...props }: React.ComponentProps<"label">) {
  return (
    <label
      data-slot="label"
      className={cn("block text-lg font-bold text-foreground", className)}
      {...props}
    />
  );
}

export { Label };
