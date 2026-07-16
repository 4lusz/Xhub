import { useQuery } from "@tanstack/react-query";

import { getCurrentUser } from "@/services/auth";
import { useAuthStore } from "@/stores/authStore";

export const currentUserKey = ["auth", "me"] as const;

/**
 * Busca o perfil do usuário autenticado (`GET /auth/me`). Habilitado
 * apenas quando há um `accessToken` -- várias telas usam este hook ao
 * mesmo tempo (Sidebar, UserMenu, AdminRoute, Settings), mas o
 * TanStack Query deduplica automaticamente e faz uma única requisição.
 */
export function useCurrentUser() {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: currentUserKey,
    queryFn: getCurrentUser,
    enabled: Boolean(accessToken),
    staleTime: 60_000,
  });
}
