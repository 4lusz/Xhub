import { useQuery } from "@tanstack/react-query";

import { api } from "@/services/api";
import type { HealthStatus } from "@/types/health";

async function fetchHealth(path: string): Promise<HealthStatus> {
  const { data } = await api.get<HealthStatus>(path);
  return data;
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => fetchHealth("/health"),
    retry: 1,
  });
}

export function useDbHealthCheck() {
  return useQuery({
    queryKey: ["health", "db"],
    queryFn: () => fetchHealth("/health/db"),
    retry: 1,
  });
}
