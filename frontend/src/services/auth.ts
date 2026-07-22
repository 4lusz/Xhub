import { api } from "@/services/api";
import type { LoginResponse, TokenResponse } from "@/types/auth";
import type { User } from "@/types/user";

/**
 * `POST /auth/login` espera `application/x-www-form-urlencoded`
 * (`OAuth2PasswordRequestForm` do FastAPI/Starlette), não JSON — os
 * campos se chamam `username`/`password` mesmo sendo e-mail/senha.
 *
 * Retorna `LoginResponse`: o par de tokens normal, OU (hoje, só para
 * administradores com pergunta de segurança configurada) um pedido de
 * segundo fator -- ver `isSecondFactorRequired`/
 * `verifySecurityAnswer`.
 */
export async function login(email: string, password: string): Promise<LoginResponse> {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);

  const { data } = await api.post<LoginResponse>("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

/** Segunda etapa do login para quem tem pergunta de segurança
 * configurada -- completa com o mesmo par de tokens de um login normal. */
export async function verifySecurityAnswer(
  pendingToken: string,
  answer: string,
): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/verify-security-answer", {
    pending_token: pendingToken,
    answer,
  });
  return data;
}

/** Configura (ou substitui) a pergunta de segurança do próprio
 * administrador autenticado. */
export async function setSecurityQuestion(question: string, answer: string): Promise<User> {
  const { data } = await api.post<User>("/auth/security-question", { question, answer });
  return data;
}

/** Remove a pergunta de segurança -- volta a autenticar só com e-mail+senha. */
export async function removeSecurityQuestion(): Promise<User> {
  const { data } = await api.delete<User>("/auth/security-question");
  return data;
}

export async function logout(refreshToken: string): Promise<void> {
  await api.post("/auth/logout", { refresh_token: refreshToken });
}

/**
 * Conclui o primeiro acesso obrigatório (ver
 * docs/ROADMAP_PRIMEIRO_ACESSO.md): troca a senha temporária pela
 * senha definitiva escolhida pelo usuário. Única rota protegida
 * acessível enquanto `mustChangePassword` for `true` no
 * `useAuthStore` (o backend aplica a mesma regra de forma
 * independente -- ver `get_current_user_for_password_change`).
 */
export async function changePassword(newPassword: string): Promise<User> {
  const { data } = await api.post<User>("/auth/change-password", {
    new_password: newPassword,
  });
  return data;
}

/**
 * Dados do usuário autenticado (`GET /auth/me`).
 *
 * Substitui o workaround anterior (e-mail capturado no formulário de
 * login + sonda contra `GET /admin/plans` para inferir o papel) agora
 * que o backend expõe esse endpoint -- fonte única e confiável de
 * nome/e-mail/papel/status do usuário logado.
 */
export async function getCurrentUser(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}
