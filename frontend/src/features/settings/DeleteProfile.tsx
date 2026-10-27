import { Trash2 } from "lucide-react";
import { AlertDialog } from "radix-ui";
import type { ReactNode } from "react";
import { useNavigate } from "react-router";

import type { Profile } from "@/shared/api/profiles";
import { Button } from "@/shared/ui/button";
import { useToast } from "@/shared/ui/toast";

import { useDeleteProfile } from "../profiles/hooks";

/**
 * Delete the profile and everything it owns (favourites, likes, feeds). It can't be undone, so
 * it asks first, in a dialog that starts on "Keep it". `children` replaces the default trigger
 * button (the profile picker uses a small icon button).
 */
export function DeleteProfile({ profile, children }: { profile: Profile; children?: ReactNode }) {
  const remove = useDeleteProfile(profile.id);
  const navigate = useNavigate();
  const toast = useToast();

  async function confirm() {
    try {
      await remove.mutateAsync();
    } catch {
      return; // The error shows in the dialog.
    }
    toast.show(`${profile.display_name}'s profile is deleted.`);
    await navigate("/profiles");
  }

  return (
    <AlertDialog.Root>
      <AlertDialog.Trigger asChild>
        {children ?? (
          <Button variant="secondary" className="self-start border-danger/40 text-danger">
            <Trash2 /> Delete this profile
          </Button>
        )}
      </AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="sheet-overlay fixed inset-0 z-40 bg-ink/35 backdrop-blur-[2px]" />
        <AlertDialog.Content className="rise-in fixed top-1/2 left-1/2 z-50 w-[min(440px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-hairline bg-surface p-6 shadow-lift outline-none">
          <AlertDialog.Title className="text-[22px] leading-tight font-semibold text-ink">
            Delete {profile.display_name}?
          </AlertDialog.Title>
          <AlertDialog.Description className="mt-2 text-body">
            This removes the profile's favourites, likes, saved items, hidden items and feeds. It
            can't be undone.
          </AlertDialog.Description>
          {remove.isError && (
            <p role="alert" className="mt-3 text-danger">
              {remove.error.message}
            </p>
          )}
          <div className="mt-6 flex flex-wrap justify-end gap-2">
            <AlertDialog.Cancel asChild>
              <Button variant="secondary">Keep it</Button>
            </AlertDialog.Cancel>
            <Button
              variant="dark"
              className="bg-danger hover:bg-danger/90"
              disabled={remove.isPending}
              onClick={() => void confirm()}
            >
              <Trash2 /> {remove.isPending ? "Deleting…" : "Delete for good"}
            </Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
