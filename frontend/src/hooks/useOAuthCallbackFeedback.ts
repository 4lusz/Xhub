import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { twitterAccountsKey } from "@/hooks/useTwitterAccounts";

/**
 * `GET /oauth/x/callback` (backend) redireciona de volta para
 * `/accounts` com `?oauth=x&status=connected` ou
 * `?oauth=x&status=error&message=...` -- não existe uma rota dedicada
 * de callback no frontend (ver `app.routes.oauth._frontend_redirect`).
 * Este hook fica no layout autenticado (ver
 * `layouts/DashboardLayout.tsx`, que engloba `/accounts` e todas as
 * demais telas autenticadas) para capturar esses parâmetros, mostrar
 * um retorno claro ao usuário e limpar a URL. Importante: a raiz `/`
 * do site (`FRONTEND_URL`) é a landing page pública, fora do layout
 * autenticado -- por isso o backend redireciona especificamente para
 * `/accounts`, não para a raiz.
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
