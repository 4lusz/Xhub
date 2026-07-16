import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  addExtraPosts,
  blockSubscription,
  expireSubscription,
  getUserSubscription,
  removeExtraPosts,
  renewSubscription,
} from "@/services/subscriptions";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/types/api";
import type { ExtraPostsPayload, RenewSubscriptionPayload } from "@/types/plan";

export const userSubscriptionKey = (userId: string) => ["admin", "users", userId, "subscription"] as const;

/**
 * Busca a assinatura de um usuário via `GET /admin/users/{id}/subscription`.
 * Substitui o campo de `subscription_id` digitado manualmente pelo
 * administrador -- o id agora é descoberto automaticamente a partir do
 * usuário selecionado.
 */
export function useUserSubscription(userId: string, enabled: boolean) {
  return useQuery({
    queryKey: userSubscriptionKey(userId),
    queryFn: () => getUserSubscription(userId),
    enabled,
    retry: false,
  });
}

function useSubscriptionAction(userId: string) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: userSubscriptionKey(userId) });
  return { toast, invalidate };
}

export function useRenewSubscription(userId: string) {
  const { toast, invalidate } = useSubscriptionAction(userId);
  return useMutation({
    mutationFn: ({ subscriptionId, payload }: { subscriptionId: string; payload: RenewSubscriptionPayload }) =>
      renewSubscription(subscriptionId, payload),
    onSuccess: () => {
      invalidate();
      toast({ variant: "success", title: "Assinatura renovada" });
    },
    onError: (error: ApiError) =>
      toast({ variant: "destructive", title: "Não foi possível renovar", description: error.message }),
  });
}

export function useBlockSubscription(userId: string) {
  const { toast, invalidate } = useSubscriptionAction(userId);
  return useMutation({
    mutationFn: (subscriptionId: string) => blockSubscription(subscriptionId),
    onSuccess: () => {
      invalidate();
      toast({ title: "Assinatura bloqueada" });
    },
    onError: (error: ApiError) =>
      toast({ variant: "destructive", title: "Não foi possível bloquear", description: error.message }),
  });
}

export function useExpireSubscription(userId: string) {
  const { toast, invalidate } = useSubscriptionAction(userId);
  return useMutation({
    mutationFn: (subscriptionId: string) => expireSubscription(subscriptionId),
    onSuccess: () => {
      invalidate();
      toast({ title: "Assinatura expirada" });
    },
    onError: (error: ApiError) =>
      toast({ variant: "destructive", title: "Não foi possível expirar", description: error.message }),
  });
}

export function useAddExtraPosts(userId: string) {
  const { toast, invalidate } = useSubscriptionAction(userId);
  return useMutation({
    mutationFn: ({ subscriptionId, payload }: { subscriptionId: string; payload: ExtraPostsPayload }) =>
      addExtraPosts(subscriptionId, payload),
    onSuccess: () => {
      invalidate();
      toast({ variant: "success", title: "Posts extras adicionados" });
    },
    onError: (error: ApiError) =>
      toast({ variant: "destructive", title: "Não foi possível adicionar posts extras", description: error.message }),
  });
}

export function useRemoveExtraPosts(userId: string) {
  const { toast, invalidate } = useSubscriptionAction(userId);
  return useMutation({
    mutationFn: ({ subscriptionId, payload }: { subscriptionId: string; payload: ExtraPostsPayload }) =>
      removeExtraPosts(subscriptionId, payload),
    onSuccess: () => {
      invalidate();
      toast({ title: "Posts extras removidos" });
    },
    onError: (error: ApiError) =>
      toast({ variant: "destructive", title: "Não foi possível remover posts extras", description: error.message }),
  });
}
