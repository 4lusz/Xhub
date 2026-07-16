import { api } from "@/services/api";
import type { TwitterAccount } from "@/types/twitterAccount";

export async function listTwitterAccounts(): Promise<TwitterAccount[]> {
  const { data } = await api.get<TwitterAccount[]>("/twitter-accounts", {
    params: { limit: 100 },
  });
  return data;
}

export async function disconnectTwitterAccount(accountId: string): Promise<void> {
  await api.delete(`/twitter-accounts/${accountId}`);
}

interface OAuthLoginResponse {
  authorization_url: string;
}

/**
 * Início do fluxo OAuth2/PKCE de conexão de conta do X.
 *
 * `GET /oauth/x/login` exige o Bearer token do usuário e responde com
 * `{ "authorization_url": "..." }` em JSON (não redireciona mais o
 * próprio backend). O frontend faz a chamada autenticada normalmente
 * via Axios (o interceptor já anexa o token) e só então navega o
 * navegador de verdade para a URL retornada.
 */
export async function getTwitterOAuthLoginUrl(): Promise<string> {
  const { data } = await api.get<OAuthLoginResponse>("/oauth/x/login");
  return data.authorization_url;
}
