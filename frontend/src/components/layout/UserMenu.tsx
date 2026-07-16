import { Link } from "react-router-dom";
import { LogOut, Settings, Shield, User as UserIcon, UserCircle } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { useLogout, useSession } from "@/hooks/useAuth";
import { initialsFromName } from "@/lib/format";

export function UserMenu() {
  const { user, isAdmin } = useSession();
  const logout = useLogout();
  const label = user?.name ?? user?.email ?? "Minha conta";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Abrir menu da conta"
        className="flex items-center gap-2 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Avatar className="h-8 w-8 border border-border">
          <AvatarFallback>{initialsFromName(label)}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col gap-1">
          <span className="flex items-center gap-2 text-sm font-medium text-foreground">
            <UserIcon className="h-3.5 w-3.5" />
            {label}
          </span>
          {user?.email && user.name && (
            <span className="pl-5 text-xs text-muted-foreground">{user.email}</span>
          )}
          {isAdmin && (
            <Badge variant="default" className="w-fit">
              <Shield className="h-3 w-3" />
              Administrador
            </Badge>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/profile">
            <UserCircle className="h-4 w-4" />
            Perfil
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to="/settings">
            <Settings className="h-4 w-4" />
            Configurações
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onSelect={() => logout.mutate()}>
          <LogOut className="h-4 w-4" />
          Sair
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
