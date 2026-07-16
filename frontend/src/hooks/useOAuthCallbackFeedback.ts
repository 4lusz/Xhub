import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { twitterAccountsKey } from "@/hooks/useTwitterAccounts";

/**
 * `GET /oauth/x/callback` (backend) redireciona de volta para a raiz
 * do frontend com `?oauth=x&status=connected` ou
 * `?oauth=x&status=error&message=...` -- não existe uma rota dedicada
 * de callback no frontend, o backend sempre volta para `FRONTEND_URL`
 * (a raiz). Este hook fica no layout autenticado (ver
 * `layouts/DashboardLayout.tsx`) para capturar esses parâmetros
 * independentemente de qual página a raiz estiver renderizando no
 * momento, mostrar um retorno claro ao usuário e limpar a URL.
 */
export function useOAuthCallbackFeedback() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  useEffect(() => {
    const oauth = searchParams.get("oauth");
    if (oauth !== "x") return;

    const status = searchParams.get("status");
    const message = searchParams.get("message");

    if (status === "connected") {
      toast({ variant: "success", title: "Conta do X conectada com sucesso" });
      queryClient.invalidateQueries({ queryKey: twitterAccountsKey });
    } else if (status === "error") {
      toast({
        variant: "destructive",
        title: "Não foi possível conectar a conta do X",
        description: message ?? undefined,
      });
    }

    const next = new URLSearchParams(searchParams);
    next.delete("oauth");
    next.delete("status");
    next.delete("message");
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);
}
