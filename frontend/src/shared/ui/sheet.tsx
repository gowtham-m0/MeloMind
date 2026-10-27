import { cn } from "cn";
import { X } from "lucide-react";
import { Dialog } from "radix-ui";
import type { ReactNode } from "react";

interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Read by screen readers as the sheet's name. */
  title: string;
  children: ReactNode;
}

/**
 * A detail sheet: a bottom sheet on phones and a right-hand drawer from 768 px. Radix traps focus,
 * closes on Escape and on the overlay, and returns focus to whatever opened it.
 */
export function Sheet({ open, onOpenChange, title, children }: SheetProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="sheet-overlay fixed inset-0 z-40 bg-ink/35 backdrop-blur-[2px]" />
        <Dialog.Content
          aria-describedby={undefined}
          className={cn(
            "sheet-panel fixed z-50 flex flex-col overflow-hidden bg-surface shadow-[0_-12px_40px_-12px_#00000040] outline-none",
            "inset-x-0 bottom-0 max-h-[92dvh] rounded-t-2xl",
            "md:inset-y-3 md:right-3 md:left-auto md:max-h-none md:w-[min(520px,calc(100vw-24px))] md:rounded-2xl md:border md:border-hairline",
          )}
        >
          <Dialog.Title className="sr-only">{title}</Dialog.Title>
          <div aria-hidden className="mx-auto mt-2.5 h-1.5 w-10 rounded-full bg-line md:hidden" />
          <Dialog.Close
            className="absolute top-3 right-3 z-10 grid size-11 place-items-center rounded-full bg-surface/90 text-ink shadow-soft backdrop-blur transition-colors hover:bg-surface-2"
            aria-label="Close"
          >
            <X className="size-5" />
          </Dialog.Close>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
