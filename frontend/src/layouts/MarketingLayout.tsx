import { Link, Outlet } from "react-router-dom";

import { Logo } from "@/components/common/Logo";
import { Button } from "@/components/ui/button";
import { CONTACT_EMAIL } from "@/lib/constants";

const NAV_LINKS = [
  { to: "/", label: "Início" },
  { to: "/sobre", label: "Sobre" },
  { to: "/faq", label: "FAQ" },
  { to: "/contato", label: "Contato" },
];

/**
 * Layout das páginas públicas de marketing/institucionais (landing,
 * sobre, contato, FAQ, privacidade, termos) -- inteiramente separado de
 * `DashboardLayout`/`AuthLayout`: sem sidebar, sem dependência de
 * sessão. Nunca renderiza nada vindo de uma rota protegida.
 */
export function MarketingLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-8">
          <Link to="/" aria-label="XHub — página inicial">
            <Logo />
          </Link>

          <nav className="hidden items-center gap-6 md:flex">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <Button asChild size="sm">
            <Link to="/login">Entrar</Link>
          </Button>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-8 px-4 py-12 sm:px-8 md:grid-cols-3">
          <div className="space-y-3">
            <Logo />
            <p className="max-w-xs text-sm text-muted-foreground">
              Gerencie múltiplas contas do X e publique em todas de uma vez, com variações
              naturais de texto geradas por IA.
            </p>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">Navegação</p>
            {NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="block text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">Legal</p>
            <Link
              to="/privacidade"
              className="block text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              Política de Privacidade
            </Link>
            <Link
              to="/termos"
              className="block text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              Termos de Uso
            </Link>
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="block text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {CONTACT_EMAIL}
            </a>
          </div>
        </div>

        <div className="border-t border-border py-4 text-center text-xs text-subtle-foreground">
          © {new Date().getFullYear()} XHub. Todos os direitos reservados.
        </div>
      </footer>
    </div>
  );
}
