import { Outlet, ScrollRestoration, useNavigate, useParams } from "react-router";

import { useLongPress } from "@/shared/hooks/useLongPress";

// Leaving Person mode takes a 3-second hold, so the person can't leave by accident.
const UNLOCK_MS = 3000;

/** Person mode: full screen, large text and no navigation. The only way out is the unlock. */
export function PersonLayout() {
  const { id } = useParams();
  const navigate = useNavigate();
  const unlock = useLongPress(() => void navigate(id ? `/profiles/${id}` : "/profiles"), UNLOCK_MS);

  return (
    <div className="fixed inset-0 flex flex-col bg-background text-2xl text-foreground">
      <div className="flex justify-end p-2">
        <button
          type="button"
          {...unlock.handlers}
          className="relative min-h-11 min-w-11 overflow-hidden rounded-md border-2 px-3 text-base text-muted-foreground select-none"
        >
          <span
            aria-hidden="true"
            className="absolute inset-y-0 left-0 bg-secondary"
            style={{ width: `${unlock.progress * 100}%` }}
          />
          <span className="relative">Caregiver: hold 3 s to leave</span>
        </button>
      </div>
      <main className="flex flex-1 items-center justify-center overflow-auto p-6">
        <Outlet />
      </main>
      <ScrollRestoration />
    </div>
  );
}
