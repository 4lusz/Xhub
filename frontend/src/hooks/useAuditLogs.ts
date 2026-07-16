import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { listAuditLogs } from "@/services/admin";

export const auditLogsKey = (page: number, pageSize: number) =>
  ["admin", "audit-logs", page, pageSize] as const;

/**
 * Trilha de auditoria paginada (`GET /admin/audit-logs`). Usa
 * `keepPreviousData` para não piscar a tabela ao trocar de página. O
 * backend não expõe contagem total, então a paginação é do tipo
 * "próxima/anterior": a página seguinte só existe se a atual veio cheia.
 */
export function useAuditLogs(page: number, pageSize = 50) {
  return useQuery({
    queryKey: auditLogsKey(page, pageSize),
    queryFn: () => listAuditLogs({ offset: page * pageSize, limit: pageSize }),
    placeholderData: keepPreviousData,
    staleTime: 15_000,
  });
}
