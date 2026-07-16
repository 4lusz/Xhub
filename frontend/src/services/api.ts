import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { ApiError, type ApiErrorBody, type ApiValidationErrorItem } from "@/types/api";
import type { TokenResponse } from "@/types/auth";
import { useAuthStore } from "@/stores/authStore";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Instância separada para o refresh de token: nunca deve passar pelo
// interceptor de resposta abaixo (evita loop infinito de 401 -> refresh
// -> 401 -> refresh...).
const refreshClient = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState();
  if (accessToken) {
    config.headers.set("Authorization", `Bearer ${accessToken}`);
  }
  return config;
});

// Evita múltiplos refreshes simultâneos quando várias requisições
// tomam 401 ao mesmo tempo: a primeira dispara o refresh, as demais
// aguardam a mesma promise.
let refreshPromise: Promise<TokenResponse> | null = null;

async function refreshSession(): Promise<TokenResponse> {
  const { refreshToken } = useAuthStore.getState();
  if (!refreshToken) {
    throw new Error("Sem refresh token disponível.");
  }

  if (!refreshPromise) {
    refreshPromise = refreshClient
      .post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken })
      .then((response) => response.data)
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

/**
 * `detail` normalmente é uma string (toda exceção de negócio do XHub
 * já vem pronta para exibição -- ver `ApiErrorBody`). Mas um 422 de
 * validação do próprio Pydantic (campo obrigatório ausente, fora do
 * intervalo, etc.) nunca passa pela conversão das rotas -- o FastAPI
 * responde antes disso, com `detail` como uma LISTA de
 * `{loc, msg, type}`. Sem este tratamento, `new ApiError(status,
 * detailArray)` vira a string "[object Object]" (coerção padrão do
 * JS ao atribuir um array/objeto a `Error.message`) -- exatamente o
 * bug relatado pelo usuário ao salvar um plano com preço inválido.
 */
function formatErrorDetail(detail: ApiErrorBody["detail"] | undefined): string | undefined {
  if (detail === undefined) return undefined;
  if (typeof detail === "string") return detail;

  return (detail as ApiValidationErrorItem[])
    .map((item) => {
      const field = item.loc[item.loc.length - 1];
      return field && typeof field === "string" ? `${field}: ${item.msg}` : item.msg;
    })
    .join("; ");
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const originalRequest = error.config as RetriableConfig | undefined;
    const status = error.response?.status;
    const url = originalRequest?.url ?? "";

    const isAuthEndpoint = url.includes("/auth/login") || url.includes("/auth/refresh");

    if (status === 401 && originalRequest && !originalRequest._retried && !isAuthEndpoint) {
      originalRequest._retried = true;
      try {
        const tokens = await refreshSession();
        useAuthStore.getState().setTokens(tokens);
        originalRequest.headers.set("Authorization", `Bearer ${tokens.access_token}`);
        return api(originalRequest);
      } catch {
        useAuthStore.getState().clearSession();
        if (typeof window !== "undefined") {
          window.location.assign("/login");
        }
        return Promise.reject(new ApiError(401, "Sessão expirada. Faça login novamente."));
      }
    }

    // Primeiro acesso obrigatório (ver docs/ROADMAP_PRIMEIRO_ACESSO.md):
    // rede de segurança -- em condições normais `ProtectedRoute` já
    // redireciona para /first-access antes de qualquer chamada gated
    // acontecer (usa a flag persistida em `useAuthStore`), mas um 428
    // aqui (ex.: flag local desatualizada por uma redefinição
    // administrativa concorrente) sincroniza o estado e força o
    // redirecionamento mesmo assim.
    if (status === 428) {
      useAuthStore.getState().setMustChangePassword(true);
      if (typeof window !== "undefined" && window.location.pathname !== "/first-access") {
        window.location.assign("/first-access");
      }
    }

    const message = formatErrorDetail(error.response?.data?.detail) ?? error.message ?? "Não foi possível completar a requisição.";

    return Promise.reject(new ApiError(status ?? 0, message));
  },
);

export function getApiBaseUrl(): string {
  return API_URL;
}
