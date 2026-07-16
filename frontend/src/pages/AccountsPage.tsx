import { useState } from "react";
import { AtSign } from "lucide-react";

import { ConnectAccountButton } from "@/components/accounts/ConnectAccountButton";
import { TwitterAccountCard } from "@/components/accounts/TwitterAccountCard";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { useDisconnectTwitterAccount, useTwitterAccounts } from "@/hooks/useTwitterAccounts";

export function AccountsPage() {
  const { data: accounts, isLoading } = useTwitterAccounts();
  const disconnect = useDisconnectTwitterAccount();
  const [pendingId, setPendingId] = useState<string | null>(null);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Contas do X"
        description="Conecte quantas contas do X quiser publicar em conjunto, respeitando o limite do seu plano."
        actions={<ConnectAccountButton />}
      />

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-20 w-full rounded-xl" />
          ))}
        </div>
      ) : !accounts || accounts.length === 0 ? (
        <EmptyState
          icon={<AtSign className="h-5 w-5" />}
          title="Nenhuma conta conectada"
          description="Conecte sua primeira conta do X para começar a publicar pelo XHub."
          action={<ConnectAccountButton />}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {accounts.map((account) => (
            <TwitterAccountCard
              key={account.id}
              account={account}
              onDisconnect={() => setPendingId(account.id)}
            />
          ))}

          <ConfirmDialog
            open={pendingId !== null}
            onOpenChange={(open) => setPendingId(open ? pendingId : null)}
            title={
              pendingId
                ? `Desconectar @${accounts.find((a) => a.id === pendingId)?.username ?? ""}?`
                : "Desconectar conta?"
            }
            description="Posts já publicados não são afetados, mas você não poderá mais publicar nesta conta até reconectá-la."
            confirmLabel="Desconectar"
            destructive
            isLoading={disconnect.isPending}
            onConfirm={() => {
              if (!pendingId) return;
              disconnect.mutate(pendingId, { onSuccess: () => setPendingId(null) });
            }}
          />
        </div>
      )}
    </div>
  );
}
