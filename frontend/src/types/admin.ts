/**
 * Tipos das telas administrativas de leitura (dashboard de métricas e
 * trilha de auditoria). Espelham exatamente `AdminStatsResponse` e
 * `AuditLogResponse` do backend (`app/routes/admin.py`).
 */

export interface AdminStats {
  total_users: number;
  active_subscriptions: number;
  blocked_subscriptions: number;
  expired_subscriptions: number;
  total_posts: number;
  published_posts: number;
}

export interface AuditLog {
  id: string;
  action: string;
  actor_user_id: string | null;
  actor_name: string | null;
  target_type: string | null;
  target_id: string | null;
  description: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

/**
 * Visão administrativa de um post (`GET /admin/posts`) — diferente de
 * `types/post.ts::PostAccount` (visão do cliente), inclui `error_message`
 * com o motivo exato retornado pela API do X em caso de falha, para
 * auditoria/suporte.
 */
export interface AdminPostAccount {
  twitter_account_id: string;
  username: string;
  status: "pending" | "published" | "failed";
  x_post_id: string | null;
  error_message: string | null;
}

export interface AdminPost {
  id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  // O conteúdo do post (texto) não é exposto ao admin — privacidade do
  // usuário. Só status (do post e por conta) e o motivo de falha.
  status: "draft" | "pending" | "scheduled" | "publishing" | "published" | "failed";
  created_at: string;
  accounts: AdminPostAccount[];
}
