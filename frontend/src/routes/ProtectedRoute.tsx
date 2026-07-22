import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useSession } from "@/hooks/useAuth";
import { useAuthStore } from "@/stores/authStore";

const FIRST_ACCESS_PATH = "/first-access";

/**
 * Além de exigir autenticação, aplica o gate de primeiro acesso
 * obrigatório (ver docs/ROADMAP_PRIMEIRO_ACESSO.md): enquanto
 * `mustChangePassword` for `true`, NENHUMA tela do sistema é
 * renderizada além da própria `/first-access` -- redireciona antes de
 * qualquer rota filha (dashboard, contas, admin, etc.) montar e
 * disparar suas próprias chamadas (que o backend rejeitaria com 428
 * de qualquer forma, mas o objetivo é nem chegar a tentar).
 */
export function ProtectedRoute() {
  const { isAuthenticated } = useSession();
  const mustChangePassword = useAuthStore((state) => state.mustChangePassword);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (mustChangePassword && location.pathname !== FIRST_ACCESS_PATH) {
    return <Navigate to={FIRST_ACCESS_PATH} replace />;
  }

  if (!mustChangePassword && location.pathname === FIRST_ACCESS_PATH) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
