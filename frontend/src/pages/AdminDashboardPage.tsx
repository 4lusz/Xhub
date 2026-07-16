import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, FileText, ShieldOff, Sparkles, TimerOff, Users } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminStats } from "@/hooks/useAdminStats";

function statValue(isLoading: boolean, value: number | undefined) {
  return isLoading ? <Skeleton className="h-8 w-12" /> : value ?? 0;
}

export function AdminDashboardPage() {
  const { data, isLoading } = useAdminStats();

  const activeSubs = data?.active_subscriptions ?? 0;
  const blockedSubs = data?.blocked_subscriptions ?? 0;
  const expiredSubs = data?.expired_subscriptions ?? 0;
  const totalSubs = activeSubs + blockedSubs + expiredSubs;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Painel administrativo"
        description="Visão agregada da plataforma. A gestão de usuários, planos e assinaturas continua nas telas dedicadas."
        actions={
          <Button asChild variant="outline">
            <Link to="/admin/users">
              <Users className="h-4 w-4" />
              Gerenciar usuários
            </Link>
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Usuários"
          value={statValue(isLoading, data?.total_users)}
          icon={<Users className="h-5 w-5" />}
          accent
        />
        <StatCard
          label="Assinaturas ativas"
          value={statValue(isLoading, data?.active_subscriptions)}
          icon={<CheckCircle2 className="h-5 w-5" />}
        />
        <StatCard
          label="Posts no sistema"
          value={statValue(isLoading, data?.total_posts)}
          icon={<FileText className="h-5 w-5" />}
        />
        <StatCard
          label="Posts publicados"
          value={statValue(isLoading, data?.published_posts)}
          icon={<Sparkles className="h-5 w-5" />}
        />
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div className="space-y-1.5">
            <CardTitle>Assinaturas por status</CardTitle>
            <CardDescription>
              {isLoading ? "—" : `${totalSubs} assinatura${totalSubs === 1 ? "" : "s"} no total`}
            </CardDescription>
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/admin/audit-logs">
              Ver auditoria
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <SubscriptionStat
            label="Ativas"
            value={statValue(isLoading, data?.active_subscriptions)}
            icon={<CheckCircle2 className="h-5 w-5" />}
            tone="success"
          />
          <SubscriptionStat
            label="Bloqueadas"
            value={statValue(isLoading, data?.blocked_subscriptions)}
            icon={<ShieldOff className="h-5 w-5" />}
            tone="destructive"
          />
          <SubscriptionStat
            label="Expiradas"
            value={statValue(isLoading, data?.expired_subscriptions)}
            icon={<TimerOff className="h-5 w-5" />}
            tone="muted"
          />
        </CardContent>
      </Card>
    </div>
  );
}

function SubscriptionStat({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  icon: React.ReactNode;
  tone: "success" | "destructive" | "muted";
}) {
  const toneClass =
    tone === "success"
      ? "text-success"
      : tone === "destructive"
        ? "text-destructive"
        : "text-muted-foreground";

  return (
    <div className="flex items-center gap-3 rounded-md border border-border bg-surface px-4 py-3">
      <span className={toneClass}>{icon}</span>
      <div>
        <div className="font-display text-2xl font-semibold tracking-tight text-foreground">{value}</div>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}
