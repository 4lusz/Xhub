import { useState } from "react";
import { Link } from "react-router-dom";
import { FileText, KeyRound, Shield, ShieldCheck, ShieldOff, Users } from "lucide-react";

import { CreateUserDialog } from "@/components/admin/CreateUserDialog";
import { ResetPasswordResultDialog } from "@/components/admin/ResetPasswordResultDialog";
import { SubscriptionActionsDialog } from "@/components/admin/SubscriptionActionsDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useChangeUserRole, useResetUserPassword, useToggleUserBlock, useUsers } from "@/hooks/useAdminUsers";
import { useSession } from "@/hooks/useAuth";
import type { ResetPasswordResult } from "@/types/user";

export function AdminUsersPage() {
  const usersQuery = useUsers();
  const toggleBlock = useToggleUserBlock();
  const changeRole = useChangeUserRole();
  const resetPassword = useResetUserPassword();
  const { userId: currentUserId } = useSession();
  const [resetResult, setResetResult] = useState<ResetPasswordResult | null>(null);

  const users = usersQuery.data ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Usuários"
        description="Crie contas e gerencie acesso. Não há autocadastro no XHub."
        actions={<CreateUserDialog />}
      />

      {usersQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      ) : users.length === 0 ? (
        <EmptyState icon={<Users className="h-5 w-5" />} title="Nenhum usuário cadastrado" />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nome</TableHead>
              <TableHead>E-mail</TableHead>
              <TableHead>Papel</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium text-foreground">{user.name}</TableCell>
                <TableCell className="text-muted-foreground">{user.email}</TableCell>
                <TableCell>
                  <Badge variant={user.role === "admin" ? "default" : "secondary"}>
                    {user.role === "admin" ? "Administrador" : "Cliente"}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1.5">
                    <Badge variant={user.is_blocked ? "destructive" : "success"}>
                      {user.is_blocked ? "Bloqueado" : "Ativo"}
                    </Badge>
                    {user.must_change_password && (
                      <Badge variant="warning">Aguardando 1º acesso</Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link to={`/admin/posts?q=${encodeURIComponent(user.email)}`}>
                        <FileText className="h-4 w-4" />
                        Posts
                      </Link>
                    </Button>
                    <SubscriptionActionsDialog userId={user.id} userName={user.name} />
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          Gerenciar
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onSelect={() =>
                            toggleBlock.mutate({ userId: user.id, block: !user.is_blocked })
                          }
                        >
                          {user.is_blocked ? (
                            <>
                              <ShieldCheck className="h-4 w-4" />
                              Desbloquear
                            </>
                          ) : (
                            <>
                              <ShieldOff className="h-4 w-4" />
                              Bloquear
                            </>
                          )}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          disabled={user.id === currentUserId}
                          onSelect={() =>
                            changeRole.mutate({
                              userId: user.id,
                              role: user.role === "admin" ? "client" : "admin",
                            })
                          }
                        >
                          <Shield className="h-4 w-4" />
                          {user.role === "admin" ? "Tornar cliente" : "Tornar admin"}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() =>
                            resetPassword.mutate(user.id, {
                              onSuccess: (result) => setResetResult(result),
                            })
                          }
                        >
                          <KeyRound className="h-4 w-4" />
                          Redefinir senha
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <ResetPasswordResultDialog result={resetResult} onClose={() => setResetResult(null)} />
    </div>
  );
}
