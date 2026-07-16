import { useQuery } from "@tanstack/react-query";

import { getAdminStats } from "@/services/admin";

export const adminStatsKey = ["admin", "stats"] as const;

/** Métricas agregadas da plataforma para o dashboard administrativo. */
export function useAdminStats() {
  return useQuery({
    queryKey: adminStatsKey,
    queryFn: getAdminStats,
    staleTime: 30_000,
  });
}
