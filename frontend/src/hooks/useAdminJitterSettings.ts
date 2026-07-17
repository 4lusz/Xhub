import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getJitterSettings, updateJitterSettings } from "@/services/jitter";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/types/api";
import type { UpdateJitterSettingsPayload } from "@/types/jitter";

export const jitterSettingsKey = ["admin", "jitter-settings"] as const;

export function useJitterSettings() {
  return useQuery({
    queryKey: jitterSettingsKey,
    queryFn: getJitterSettings,
  });
}

export function useUpdateJitterSettings() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (payload: UpdateJitterSettingsPayload) => updateJitterSettings(payload),
    onSuccess: (settings) => {
      queryClient.setQueryData(jitterSettingsKey, settings);
      toast({ variant: "success", title: "Configuração do Jitter atualizada" });
    },
    onError: (error: ApiError) => {
      toast({
        variant: "destructive",
        title: "Não foi possível atualizar a configuração",
        description: error.message,
      });
    },
  });
}
