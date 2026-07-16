import { api } from "@/services/api";
import type { AdminPost, AdminStats, AuditLog } from "@/types/admin";

/** Métricas agregadas da plataforma (`GET /admin/stats`). */
export async function getAdminStats(): Promise<AdminStats> {
  const { data } = await api.get<AdminStats>("/admin/stats");
  return data;
}

/**
 * Posts de todos os usuários, com o motivo exato de falha por conta
 * (`GET /admin/posts`) — somente leitura, para auditoria e suporte.
 */
export async function listAdminPosts(params?: {
  status?: string;
  offset?: number;
  limit?: number;
}): Promise<AdminPost[]> {
  const { data } = await api.get<AdminPost[]>("/admin/posts", {
    params: {
      status_filter: params?.status,
      offset: params?.offset ?? 0,
      limit: params?.limit ?? 50,
    },
  });
  return data;
}

/** Trilha de auditoria paginada (`GET /admin/audit-logs`). */
export async function listAuditLogs(params?: {
  offset?: number;
  limit?: number;
}): Promise<AuditLog[]> {
  const { data } = await api.get<AuditLog[]>("/admin/audit-logs", {
    params: { offset: params?.offset ?? 0, limit: params?.limit ?? 50 },
  });
  return data;
}
