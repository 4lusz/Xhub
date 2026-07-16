import { RefreshCw, Shield } from "lucide-react";

import { EditPlanDialog } from "@/components/admin/EditPlanDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePlans, useSyncPlans } from "@/hooks/useAdminPlans";

const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

export function AdminPlansPage() {
  const plansQuery = usePlans();
  const syncPlans = useSyncPlans();

  const plans = plansQuery.data ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Planos"
        description="Limites e características vêm do catálogo oficial. O preço é definido manualmente por um administrador."
        actions={
          <Button variant="outline" onClick={() => syncPlans.mutate()} disabled={syncPlans.isPending}>
            <RefreshCw className={syncPlans.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            Sincronizar catálogo
          </Button>
        }
      />

      {plansQuery.isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-40 w-full rounded-xl" />
          ))}
        </div>
      ) : plans.length === 0 ? (
        <EmptyState
          icon={<Shield className="h-5 w-5" />}
          title="Nenhum plano encontrado"
          description="Sincronize o catálogo oficial para popular os planos."
          action={
            <Button size="sm" onClick={() => syncPlans.mutate()}>
              Sincronizar agora
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {plans.map((plan) => (
            <Card key={plan.id}>
              <CardHeader>
                <CardTitle className="text-base">{plan.name}</CardTitle>
                <CardDescription className="font-display text-2xl font-semibold text-foreground">
                  {currencyFormatter.format(plan.price)}
                  <span className="text-sm font-normal text-muted-foreground">/mês</span>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <dl className="space-y-1.5 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-muted-foreground">Contas do X</dt>
                    <dd className="font-medium text-foreground">{plan.max_accounts}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted-foreground">Posts/mês</dt>
                    <dd className="font-medium text-foreground">{plan.max_posts_month}</dd>
                  </div>
                </dl>
                <EditPlanDialog plan={plan} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
