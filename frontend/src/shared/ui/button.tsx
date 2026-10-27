import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "cn";
import { Slot } from "radix-ui";
import type { ComponentProps } from "react";

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-lg font-medium whitespace-nowrap transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-(--ease-out) active:translate-y-px disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-[18px]",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-ink hover:-translate-y-px hover:bg-primary-hover hover:shadow-[0_4px_14px_-4px_#e8a83880]",
        secondary:
          "border border-[#ddd] bg-surface text-ink hover:-translate-y-px hover:border-[#bbb] hover:shadow-soft",
        ghost: "text-ink hover:bg-surface-2",
        onImage: "border border-white/40 bg-white/15 text-white backdrop-blur-md hover:bg-white/25",
        dark: "bg-ink text-white hover:-translate-y-px hover:bg-[#333]",
      },
      size: {
        md: "h-11 px-5 text-[15px]",
        lg: "h-12 px-6 text-base",
        sm: "h-9 px-3.5 text-sm pointer-coarse:h-11",
        icon: "size-11",
        "icon-sm": "size-9 pointer-coarse:size-11",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

type ButtonProps = ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    /** Render the child element (a link, say) with button styles. */
    asChild?: boolean;
  };

/** The app's button: amber primary, white secondary, ghost, on-image glass and dark. */
export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot.Root : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
