export type UserRole = "client" | "admin";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  is_blocked: boolean;
  must_change_password: boolean;
  /** Texto da pergunta de segurança configurada (2º fator de login,
   * hoje restrito a administradores) -- `null` quando não configurada. */
  security_question: string | null;
}

export interface CreateUserPayload {
  name: string;
  email: string;
  password: string;
  role: UserRole;
  plan_id: string;
  subscription_expires_at: string;
}

/**
 * Resposta da redefinição administrativa de senha (ver
 * docs/ROADMAP_PRIMEIRO_ACESSO.md) -- `temporary_password` é exibida
 * uma única vez, nunca recuperável depois.
 */
export interface ResetPasswordResult {
  user: User;
  temporary_password: string;
}
