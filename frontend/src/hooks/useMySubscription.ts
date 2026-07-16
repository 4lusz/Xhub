import { useQuery } from "@tanstack/react-query";

import { getMySubscription } from "@/services/subscriptions";
import { useAuthStore } from "@/stores/authStore";

export const mySubscriptionKey = ["me", "subscription"] as const;

/**
 * Assinatura vigente do próprio usuário (`GET /me/subscription`) — plano,
 * limites e consumo. Habilitado apenas quando há sessão. `retry: false`
 * porque um 404 é esperado para contas administrativas (criadas sem
 * assinatura): nesse caso o indicador simplesmente não é exibido, sem
 * novas tentativas.
 */
export function useMySubscription() {
  const accessToken = useAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: mySubscriptionKey,
    queryFn: getMySubscription,
    enabled: Boolean(accessToken),
    retry: false,
    staleTime: 60_000,
  });
}
