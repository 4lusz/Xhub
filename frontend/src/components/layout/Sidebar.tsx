import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  CalendarClock,
  FileText,
  LayoutDashboard,
  Menu,
  Settings,
  Shield,
  Sparkles,
  AtSign,
  UserCircle,
  Users,
} from "lucide-react";

import { Logo } from "@/components/common/Logo";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { useSession } from "@/hooks/useAuth";

interface NavItemConfig {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  end?: boolean;
}

const primaryNav: NavItemConfig[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/accounts", label: "Contas do X", icon: AtSign },
  { to: "/posts", label: "Histórico", icon: Sparkles },
  { to: "/scheduled", label: "Agendamentos", icon: CalendarClock },
];

const secondaryNav: NavItemConfig[] = [
  { to: "/profile", label: "Perfil", icon: UserCircle },
  { to: "/settings", label: "Configurações", icon: Settings },
];

// Navegação exclusiva do administrador: só telas de gestão da
// plataforma. Um admin não usa o XHub como cliente (não publica posts,
// não conecta contas do X -- contas admin não possuem assinatura por
// design, ver ClientOnlyRoute), então essa lista substitui inteiramente
// o `primaryNav` quando `isAdmin`, em vez de conviver com ele.
const adminNav: NavItemConfig[] = [
  { to: "/admin", label: "Painel", icon: LayoutDashboard, end: true },
  { to: "/admin/users", label: "Usuários", icon: Users },
  { to: "/admin/plans", label: "Planos", icon: Shield },
  { to: "/admin/posts", label: "Publicações", icon: FileText },
  { to: "/admin/audit-logs", label: "Auditoria", icon: Shield },
];

function NavItem({ to, label, icon: Icon, end, onNavigate }: NavItemConfig & { onNavigate?: () => void }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-primary/15 text-primary"
            : "text-muted-foreground hover:bg-surface-hover hover:text-foreground",
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </NavLink>
  );
}

/**
 * Conteúdo interno da sidebar (logo + navegação), compartilhado entre a
 * versão fixa de desktop (`Sidebar`) e o drawer mobile (`MobileSidebar`).
 * `onNavigate` é chamado ao clicar em qualquer link -- usado no mobile
 * para fechar o drawer após a navegação.
 */
function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const { isAdmin } = useSession();

  return (
    <>
      <div className="px-2">
        <Logo />
      </div>

      {isAdmin ? (
        <div className="mt-8 px-3">
          <p className="text-xs font-medium uppercase tracking-wide text-subtle-foreground">
            Administração
          </p>
        </div>
      ) : (
        <div className="mt-8">
          <Button asChild className="w-full justify-start gap-2" size="default">
            <NavLink to="/posts/new" onClick={onNavigate}>
              <Sparkles className="h-4 w-4" />
              Novo post
            </NavLink>
          </Button>
        </div>
      )}

      <nav className="mt-6 flex flex-1 flex-col gap-1">
        {(isAdmin ? adminNav : primaryNav).map((item) => (
          <NavItem key={item.to} {...item} onNavigate={onNavigate} />
        ))}

        <Separator className="my-3" />
        {secondaryNav.map((item) => (
          <NavItem key={item.to} {...item} onNavigate={onNavigate} />
        ))}
      </nav>
    </>
  );
}

/** Sidebar fixa de desktop -- escondida abaixo do breakpoint `md`. */
export function Sidebar() {
  return (
    <aside className="hidden h-screen w-64 shrink-0 flex-col border-r border-border bg-surface/60 px-4 py-5 md:flex">
      <SidebarNav />
    </aside>
  );
}

/**
 * Menu hambúrguer + drawer para telas pequenas. Renderiza apenas abaixo
 * do breakpoint `md` (onde a `Sidebar` fixa fica escondida).
 */
export function MobileSidebar() {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Abrir menu de navegação">
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="flex flex-col px-4 py-5">
        <SheetTitle className="sr-only">Menu de navegação</SheetTitle>
        <SidebarNav onNavigate={() => setOpen(false)} />
      </SheetContent>
    </Sheet>
  );
}
