import { CreditCard } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useMySubscription } from "@/hooks/useMySubscription";
import { formatDate } from "@/lib/format";
import type { SubscriptionStatus } from "@/types/plan";

const statusLabels: Record<SubscriptionStatus, string> = {
  active: "Ativa",
  expired: "Expirada",
  blocked: "Bloqueada",
};

const statusVariants: Record<SubscriptionStatus, "success" | "secondary" | "destructive"> = {
  active: "success",
  expired: "secondary",
  blocked: "destructive",
};

function UsageMeter({ label, used, limit, extra }: { label: string; used: number; limit: number; extra?: number }) {
  const total = limit + (extra ?? 0);
  const ratio = total > 0 ? Math.min(100, (used / total) * 100) : 0;
  const nearLimit = ratio >= 90;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono-xhub text-xs text-foreground">
          {used} / {total}
          {extra ? ` (${limit} + ${extra} extras)` : ""}
        </span>
      </div>
      <Progress value={ratio} indicatorClassName={nearLimit ? "bg-destructive" : undefined} />
    </div>
  );
}

/**
 * Indicador de plano/créditos do cliente (`GET /me/subscription`): plano
 * vigente, posts usados/limite e contas usadas/limite. Não é renderizado
 * quando o usuário não possui assinatura (ex.: contas administrativas,
 * que recebem 404 do endpoint) -- ver `useMySubscription`.
 */
export function SubscriptionCard() {
  const { data, isLoading, isError } = useMySubscription();

  if (isError) return null;

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div className="space-y-1.5">
          <CardTitle className="flex items-center gap-2 text-base">
            <CreditCard className="h-4 w-4" />
            Seu plano
          </CardTitle>
          <CardDescription>
            {isLoading ? <Skeleton className="h-4 w-24" /> : data?.plan.name ?? "—"}
          </CardDescription>
        </div>
        {!isLoading && data && (
          <Badge variant={statusVariants[data.status]}>{statusLabels[data.status]}</Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-5">
        {isLoading || !data ? (
          <div className="space-y-4">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : (
          <>
            <UsageMeter
              label="Posts usados no ciclo"
              used={data.used_posts}
              limit={data.plan.max_posts_month}
              extra={data.extra_posts}
            />
            <UsageMeter
              label="Contas do X conectadas"
              used={data.used_accounts}
              limit={data.plan.max_accounts}
            />
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Vigente até</span>
              <span className="font-medium text-foreground">{formatDate(data.expires_at)}</span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
