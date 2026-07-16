import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listPlans, syncPlans, updatePlan } from "@/services/plans";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/types/api";
import type { UpdatePlanPayload } from "@/types/plan";

export const plansKey = ["admin", "plans"] as const;

export function usePlans() {
  return useQuery({
    queryKey: plansKey,
    queryFn: listPlans,
  });
}

export function useSyncPlans() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: syncPlans,
    onSuccess: (plans) => {
      queryClient.invalidateQueries({ queryKey: plansKey });
      toast({ variant: "success", title: "Catálogo sincronizado", description: `${plans.length} planos atualizados.` });
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Falha ao sincronizar planos", description: error.message });
    },
  });
}

export function useUpdatePlan() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ planId, payload }: { planId: string; payload: UpdatePlanPayload }) =>
      updatePlan(planId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: plansKey });
      toast({ variant: "success", title: "Plano atualizado" });
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Não foi possível atualizar o plano", description: error.message });
    },
  });
}
