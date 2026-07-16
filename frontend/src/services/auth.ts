import { api } from "@/services/api";
import type { TokenResponse } from "@/types/auth";
import type { User } from "@/types/user";

/**
 * `POST /auth/login` espera `application/x-www-form-urlencoded`
 * (`OAuth2PasswordRequestForm` do FastAPI/Starlette), não JSON — os
 * campos se chamam `username`/`password` mesmo sendo e-mail/senha.
 */
export async function login(email: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);

  const { data } = await api.post<TokenResponse>("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
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
