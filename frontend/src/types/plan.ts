export interface Plan {
  id: string;
  name: string;
  price: number;
  max_accounts: number;
  max_posts_month: number;
}

export interface UpdatePlanPayload {
  price: number;
  max_accounts: number;
  max_posts_month: number;
}

export type SubscriptionStatus = "active" | "expired" | "blocked";

export interface Subscription {
  id: string;
  user_id: string;
  plan_id: string;
  status: SubscriptionStatus;
  expires_at: string;
  renewed_at: string | null;
  used_posts: number;
  extra_posts: number;
  // Consumo derivado, mesma politica de dominio de MySubscription --
  // agora tambem exposto ao admin (ver GET /admin/users/{id}/subscription).
  available_posts: number;
  used_accounts: number;
  plan: Plan;
}

/**
 * Assinatura vigente do próprio usuário autenticado (`GET /me/subscription`).
 * Diferente de `Subscription` (visão administrativa), inclui o plano
 * associado e os campos derivados de consumo (`available_posts`,
 * `used_accounts`) que o indicador de plano/créditos do cliente exibe.
 */
export interface MySubscription {
  id: string;
  status: SubscriptionStatus;
  expires_at: string;
  renewed_at: string | null;
  used_posts: number;
  extra_posts: number;
  available_posts: number;
  used_accounts: number;
  plan: Plan;
}

export interface RenewSubscriptionPayload {
  expires_at: string;
  plan_id?: string | null;
}

export interface ExtraPostsPayload {
  amount: number;
}
