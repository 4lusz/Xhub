import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  disconnectTwitterAccount,
  listTwitterAccounts,
} from "@/services/twitterAccounts";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/types/api";

export const twitterAccountsKey = ["twitter-accounts"] as const;

export function useTwitterAccounts() {
  return useQuery({
    queryKey: twitterAccountsKey,
    queryFn: listTwitterAccounts,
  });
}

export function useDisconnectTwitterAccount() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: disconnectTwitterAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: twitterAccountsKey });
      toast({ title: "Conta desconectada" });
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Não foi possível desconectar", description: error.message });
    },
  });
}
