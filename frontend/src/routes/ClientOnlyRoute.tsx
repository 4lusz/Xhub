import { Navigate, Outlet } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { useSession } from "@/hooks/useAuth";

/**
 * Guarda as telas de uso do produto (dashboard, contas, posts,
 * agendamentos) para clientes. Administradores não possuem assinatura
 * por design (contas admin não recebem `Subscription`, ver
 * `POST /admin/users`) e portanto não conseguem de fato usar esses
 * fluxos -- toda ação relevante (conectar conta, publicar) seria
 * rejeitada pelo backend por falta de assinatura ativa. Em vez de expor
 * telas que terminam em erro, o administrador é redirecionado para o
 * painel administrativo (`/admin`), espelhando o `AdminRoute` (que faz o
 * caminho inverso para clientes tentando acessar `/admin/*`).
 */
export function ClientOnlyRoute() {
  const { isAdmin, isLoadingUser } = useSession();

  if (isLoadingUser) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isAdmin) {
    return <Navigate to="/admin" replace />;
  }

  return <Outlet />;
}
