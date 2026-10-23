import { useParams } from "react-router";

import { RequireSession } from "@/features/demo/RequireSession";
import { SessionView } from "@/features/sessions/SessionView";

/** A session: the agent's log while planning, then review, approval and completion. */
export function SessionPage() {
  const { id } = useParams();

  return (
    <RequireSession>
      <SessionView sessionId={id} />
    </RequireSession>
  );
}
