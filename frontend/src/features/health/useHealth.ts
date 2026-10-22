import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/shared/api/health";

/** Reads the backend's health check. */
export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: getHealth });
}
