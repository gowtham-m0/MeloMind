import { useParams } from "react-router";

import { RequireSession } from "@/features/demo/RequireSession";
import { SessionPlayer } from "@/features/sessions/SessionPlayer";

/** Play an approved session, with prompts and reaction buttons for the caregiver. */
export function SessionPlayPage() {
  const { id } = useParams();

  return (
    <RequireSession>
      <SessionPlayer sessionId={id} />
    </RequireSession>
  );
}
