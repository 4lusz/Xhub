import { Link } from "react-router-dom";
import { Home } from "lucide-react";

import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-4 text-center">
      <p className="font-display text-6xl font-semibold text-primary">404</p>
      <p className="text-sm text-muted-foreground">Essa página não existe.</p>
      <Button asChild>
        <Link to="/">
          <Home className="h-4 w-4" />
          Voltar ao início
        </Link>
      </Button>
    </div>
  );
}
