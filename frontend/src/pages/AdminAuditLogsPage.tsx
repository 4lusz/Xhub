import { useState } from "react";
import { ChevronLeft, ChevronRight, ScrollText } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuditLogs } from "@/hooks/useAuditLogs";
import { formatDateTime } from "@/lib/format";

const PAGE_SIZE = 50;

// Rótulos legíveis para cada `AuditAction` do backend. Ações
// desconhecidas (enum novo ainda não mapeado) caem no próprio valor cru.
const actionLabels: Record<string, string> = {
  user_created: "Usuário criado",
  user_blocked: "Usuário bloqueado",
  user_unblocked: "Usuário desbloqueado",
  user_role_changed: "Papel alterado",
  subscription_created: "Assinatura criada",
  subscription_renewed: "Assinatura renovada",
  subscription_blocked: "Assinatura bloqueada",
  subscription_expired: "Assinatura expirada",
  extra_posts_added: "Posts extras adicionados",
  extra_posts_removed: "Posts extras removidos",
  plan_synced: "Planos sincronizados",
  plan_updated: "Plano atualizado",
  twitter_account_connected: "Conta do X conectada",
  twitter_account_disconnected: "Conta do X desconectada",
  other: "Outra ação",
};

export function AdminAuditLogsPage() {
  const [page, setPage] = useState(0);
  const { data, isLoading, isPlaceholderData } = useAuditLogs(page, PAGE_SIZE);

  const logs = data ?? [];
  const hasNextPage = logs.length === PAGE_SIZE;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Auditoria"
        description="Trilha de todas as ações administrativas registradas na plataforma, das mais recentes para as mais antigas."
      />

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      ) : logs.length === 0 ? (
        <EmptyState
          icon={<ScrollText className="h-5 w-5" />}
          title="Nenhum registro de auditoria"
          description={page === 0 ? undefined : "Não há mais registros nesta página."}
        />
      ) : (
        <div className="space-y-4">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="whitespace-nowrap">Data/hora</TableHead>
                  <TableHead>Ação</TableHead>
                  <TableHead>Autor</TableHead>
                  <TableHead>Alvo</TableHead>
                  <TableHead>Descrição</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                      {formatDateTime(log.created_at)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{actionLabels[log.action] ?? log.action}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {log.actor_name ?? "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {log.target_type ?? "—"}
                    </TableCell>
                    <TableCell className="max-w-sm text-foreground">
                      {log.description ?? "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-subtle-foreground">Página {page + 1}</span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((current) => Math.max(0, current - 1))}
                disabled={page === 0 || isPlaceholderData}
              >
                <ChevronLeft className="h-4 w-4" />
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((current) => current + 1)}
                disabled={!hasNextPage || isPlaceholderData}
              >
                Próxima
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
