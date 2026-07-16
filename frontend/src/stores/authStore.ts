import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { JwtPayload } from "@/types/auth";

/**
 * Estado de sessão do XHub — apenas os tokens e o `userId` (decodificado
 * do JWT, só para exibição/roteamento, nunca para decisões de
 * segurança). Dados de perfil (nome, e-mail, papel) NÃO ficam aqui:
 * vêm de `GET /auth/me` via `hooks/useCurrentUser.ts`, cacheados pelo
 * TanStack Query -- evita duplicar a mesma informação em dois lugares
 * (zustand + query cache) e mantém uma única fonte de verdade que se
 * revalida sozinha.
 */
interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  /**
   * Primeiro acesso obrigatório (ver docs/ROADMAP_PRIMEIRO_ACESSO.md):
   * persistido aqui (não só no cache do TanStack Query) porque
   * `ProtectedRoute` precisa decidir o redirecionamento de forma
   * síncrona, inclusive logo após um F5 -- antes de qualquer chamada a
   * `GET /auth/me` (que ficaria bloqueada com 428 enquanto for `true`).
   * Atualizado a cada `setTokens` (login/refresh) e explicitamente por
   * `setMustChangePassword` ao concluir a troca.
   */
  mustChangePassword: boolean;
  setTokens: (tokens: {
    access_token: string;
    refresh_token: string;
    must_change_password: boolean;
  }) => void;
  setMustChangePassword: (value: boolean) => void;
  clearSession: () => void;
}

function decodeUserId(accessToken: string): string | null {
  try {
    const payloadSegment = accessToken.split(".")[1];
    if (!payloadSegment) return null;
    const json = atob(payloadSegment.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json) as JwtPayload;
    return payload.sub ?? null;
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      userId: null,
      mustChangePassword: false,

      setTokens: (tokens) => {
        set({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          userId: decodeUserId(tokens.access_token),
          mustChangePassword: tokens.must_change_password,
        });
      },

      setMustChangePassword: (value) => set({ mustChangePassword: value }),

      clearSession: () =>
        set({
          accessToken: null,
          refreshToken: null,
          userId: null,
          mustChangePassword: false,
        }),
    }),
    {
      name: "xhub-auth",
    },
  ),
);
