import { Link } from "react-router-dom";
import { Home } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useSession } from "@/hooks/useAuth";

export function NotFoundPage() {
  // Logado -> volta para o próprio painel; anônimo -> página principal
  // pública. Nunca manda um usuário autenticado de volta para a
  // landing page de marketing por engano.
  const { isAuthenticated } = useSession();
  const homePath = isAuthenticated ? "/dashboard" : "/";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-4 text-center">
      <p className="font-display text-6xl font-semibold text-primary">404</p>
      <p className="text-sm text-muted-foreground">Essa página não existe.</p>
      <Button asChild>
        <Link to={homePath}>
          <Home className="h-4 w-4" />
          Voltar ao início
        </Link>
      </Button>
    </div>
  );
}
