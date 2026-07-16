import { useState } from "react";
import { Loader2, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { getTwitterOAuthLoginUrl } from "@/services/twitterAccounts";
import type { ApiError } from "@/types/api";

/**
 * Inicia o fluxo OAuth2/PKCE: busca a URL de autorização autenticada
 * (`GET /oauth/x/login`, que exige o Bearer token e devolve JSON) e só
 * então navega o navegador para o X — a navegação em si não pode
 * carregar o header de autenticação, por isso a busca acontece antes,
 * via Axios.
 */
export function ConnectAccountButton() {
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleConnect = async () => {
    setIsLoading(true);
    try {
      const authorizationUrl = await getTwitterOAuthLoginUrl();
      window.location.href = authorizationUrl;
    } catch (error) {
      setIsLoading(false);
      toast({
        variant: "destructive",
        title: "Não foi possível iniciar a conexão com o X",
        description: (error as ApiError).message,
      });
    }
  };

  return (
    <Button onClick={handleConnect} disabled={isLoading}>
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
      Conectar conta do X
    </Button>
  );
}
