import { useParams } from "react-router";

import { RequireSession } from "@/features/demo/RequireSession";
import { PersonMode } from "@/features/person-mode/PersonMode";

/** Person mode: the shelf and the warm-up, chosen by tapping large cards. */
export function PersonModePage() {
  const { id } = useParams();

  return <RequireSession>{id && <PersonMode profileId={id} />}</RequireSession>;
}
