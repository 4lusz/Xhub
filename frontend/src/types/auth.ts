export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  /** Primeiro acesso obrigatório: `true` enquanto a conta ainda usa uma senha temporária. */
  must_change_password: boolean;
}

/**
 * Retornado por `POST /auth/login` no lugar de `TokenResponse` quando o
 * usuário (hoje, sempre um administrador) configurou uma pergunta de
 * segurança (2º fator simples de login, ver docs/AUDITORIA_SEGURANCA.md).
 * `pending_token` só serve para `POST /auth/verify-security-answer` --
 * nunca é um token de acesso válido.
 */
export interface SecondFactorRequiredResponse {
  requires_second_factor: true;
  pending_token: string;
  question: string;
}

export type LoginResponse = TokenResponse | SecondFactorRequiredResponse;

export function isSecondFactorRequired(
  response: LoginResponse,
): response is SecondFactorRequiredResponse {
  return "requires_second_factor" in response;
}

export interface JwtPayload {
  sub: string;
  exp: number;
}
