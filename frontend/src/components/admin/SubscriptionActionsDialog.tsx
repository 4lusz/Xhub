import { useState } from "react";
import { AlertCircle, CreditCard, Loader2, MinusCircle, PlusCircle, ShieldOff, Timer } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { DateTimePicker } from "@/components/common/DateTimePicker";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAddExtraPosts,
  useBlockSubscription,
  useExpireSubscription,
  useRemoveExtraPosts,
  useRenewSubscription,
  useUserSubscription,
} from "@/hooks/useAdminSubscriptions";
import { formatDateTime } from "@/lib/format";

const STATUS_LABEL: Record<string, "success" | "destructive" | "secondary"> = {
  active: "success",
  blocked: "destructive",
  expired: "secondary",
};

interface SubscriptionActionsDialogProps {
  userId: string;
  userName: string;
}

/**
 * Busca a assinatura do usuário automaticamente via
 * `GET /admin/users/{id}/subscription` assim que o diálogo abre -- não
 * exige mais que o administrador saiba o `subscription_id` de antemão.
 */
export function SubscriptionActionsDialog({ userId, userName }: SubscriptionActionsDialogProps) {
  const [open, setOpen] = useState(false);
  const [expiresAt, setExpiresAt] = useState("");
  const [extraAmount, setExtraAmount] = useState("10");

  const subscriptionQuery = useUserSubscription(userId, open);
  const subscription = subscriptionQuery.data;
  const subscriptionId = subscription?.id;

  const renew = useRenewSubscription(userId);
  const block = useBlockSubscription(userId);
  const expire = useExpireSubscription(userId);
  const addExtra = useAddExtraPosts(userId);
  const removeExtra = useRemoveExtraPosts(userId);

  const isBusy =
    renew.isPending || block.isPending || expire.isPending || addExtra.isPending || removeExtra.isPending;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <CreditCard className="h-3.5 w-3.5" />
          Assinatura
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Assinatura de {userName}</DialogTitle>
          <DialogDescription>
            Renove, bloqueie, expire ou ajuste o saldo extra de posts.
          </DialogDescription>
        </DialogHeader>

        {subscriptionQuery.isLoading && (
          <div className="space-y-2">
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-2/3" />
          </div>
        )}

        {subscriptionQuery.isError && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>
              Não foi possível carregar a assinatura deste usuário. Ele pode não ter nenhuma
              assinatura ativa.
            </AlertDescription>
          </Alert>
        )}

        {subscription && (
          <>
            <div className="grid grid-cols-2 gap-3 rounded-lg border border-border bg-surface p-3 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">Plano</p>
                <p className="font-medium text-foreground">{subscription.plan.name}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Status</p>
                <Badge variant={STATUS_LABEL[subscription.status] ?? "secondary"}>
                  {subscription.status}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Expira em</p>
                <p className="font-medium text-foreground">{formatDateTime(subscription.expires_at)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Posts extras</p>
                <p className="font-medium text-foreground">{subscription.extra_posts}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Posts usados</p>
                <p className="font-medium text-foreground">
                  {subscription.used_posts} / {subscription.plan.max_posts_month}
                  <span className="text-xs text-muted-foreground"> ({subscription.available_posts} restantes)</span>
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Contas do X</p>
                <p className="font-medium text-foreground">
                  {subscription.used_accounts} / {subscription.plan.max_accounts}
                </p>
              </div>
            </div>

            <Separator />

            <div className="space-y-3">
              <div className="flex items-end gap-2">
                <div className="flex-1 space-y-2">
                  <Label className="flex items-center gap-1.5 text-xs">
                    <Timer className="h-3.5 w-3.5" />
                    Nova data de expiração
                  </Label>
                  <DateTimePicker value={expiresAt} onChange={setExpiresAt} />
                </div>
                <Button
                  variant="secondary"
                  disabled={!subscriptionId || !expiresAt || isBusy}
                  onClick={() =>
                    subscriptionId &&
                    renew.mutate({
                      subscriptionId,
                      payload: { expires_at: new Date(expiresAt).toISOString() },
                    })
                  }
                >
                  {renew.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Renovar"}
                </Button>
              </div>

              <div className="flex items-end gap-2">
                <div className="flex-1 space-y-2">
                  <Label className="flex items-center gap-1.5 text-xs">
                    <PlusCircle className="h-3.5 w-3.5" />
                    Posts extras
                  </Label>
                  <Input
                    type="number"
                    min={1}
                    value={extraAmount}
                    onChange={(event) => setExtraAmount(event.target.value)}
                  />
                </div>
                <Button
                  variant="secondary"
                  disabled={!subscriptionId || isBusy}
                  onClick={() =>
                    subscriptionId &&
                    addExtra.mutate({ subscriptionId, payload: { amount: Number(extraAmount) } })
                  }
                >
                  <PlusCircle className="h-4 w-4" />
                  Adicionar
                </Button>
                <Button
                  variant="outline"
                  disabled={!subscriptionId || isBusy}
                  onClick={() =>
                    subscriptionId &&
                    removeExtra.mutate({ subscriptionId, payload: { amount: Number(extraAmount) } })
                  }
                >
                  <MinusCircle className="h-4 w-4" />
                  Remover
                </Button>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  disabled={!subscriptionId || isBusy}
                  onClick={() => subscriptionId && block.mutate(subscriptionId)}
                >
                  <ShieldOff className="h-4 w-4" />
                  Bloquear
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  disabled={!subscriptionId || isBusy}
                  onClick={() => subscriptionId && expire.mutate(subscriptionId)}
                >
                  Expirar agora
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
