import { Link } from "react-router-dom";
import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  Sparkles,
  AtSign,
  XCircle,
} from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { StatCard } from "@/components/dashboard/StatCard";
import { SubscriptionCard } from "@/components/dashboard/SubscriptionCard";
import { PostStatusBadge } from "@/components/posts/PostStatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useHealthCheck } from "@/hooks/useHealthCheck";
import { usePosts } from "@/hooks/usePosts";
import { useTwitterAccounts } from "@/hooks/useTwitterAccounts";
import { formatRelativeTime, truncate } from "@/lib/format";

export function DashboardPage() {
  const postsQuery = usePosts();
  const accountsQuery = useTwitterAccounts();
  const health = useHealthCheck();

  const posts = postsQuery.data ?? [];
  const published = posts.filter((post) => post.status === "published").length;
  const scheduled = posts.filter((post) => post.status === "scheduled").length;
  const failed = posts.filter((post) => post.status === "failed").length;
  const recentPosts = [...posts]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  const isHealthy = health.data?.status === "ok";

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description="Visão geral das suas contas e publicações no XHub."
        actions={
          <Button asChild>
            <Link to="/posts/new">
              <Sparkles className="h-4 w-4" />
              Novo post
            </Link>
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Contas conectadas"
          value={accountsQuery.isLoading ? <Skeleton className="h-8 w-10" /> : accountsQuery.data?.length ?? 0}
          icon={<AtSign className="h-5 w-5" />}
          accent
        />
        <StatCard
          label="Publicados"
          value={postsQuery.isLoading ? <Skeleton className="h-8 w-10" /> : published}
          icon={<CheckCircle2 className="h-5 w-5" />}
        />
        <StatCard
          label="Agendados"
          value={postsQuery.isLoading ? <Skeleton className="h-8 w-10" /> : scheduled}
          icon={<CalendarClock className="h-5 w-5" />}
        />
        <StatCard
          label="Falharam"
          value={postsQuery.isLoading ? <Skeleton className="h-8 w-10" /> : failed}
          icon={<XCircle className="h-5 w-5" />}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle>Atividade recente</CardTitle>
            <Button asChild variant="ghost" size="sm">
              <Link to="/posts">
                Ver histórico
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {postsQuery.isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-14 w-full" />
                ))}
              </div>
            ) : recentPosts.length === 0 ? (
              <EmptyState
                icon={<Sparkles className="h-5 w-5" />}
                title="Nenhum post ainda"
                description="Crie sua primeira publicação para vê-la aqui."
                action={
                  <Button asChild size="sm">
                    <Link to="/posts/new">Criar post</Link>
                  </Button>
                }
              />
            ) : (
              <ul className="divide-y divide-border">
                {recentPosts.map((post) => (
                  <li key={post.id} className="flex items-center justify-between gap-4 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm text-foreground">{truncate(post.text, 80)}</p>
                      <p className="text-xs text-subtle-foreground">
                        {formatRelativeTime(post.created_at)}
                      </p>
                    </div>
                    <PostStatusBadge status={post.status} />
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <SubscriptionCard />

          <Card>
            <CardHeader>
              <CardTitle>Status do sistema</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between rounded-md border border-border bg-surface px-3 py-2.5">
                <span className="text-sm text-muted-foreground">API</span>
                <Badge variant={health.isLoading ? "secondary" : isHealthy ? "success" : "destructive"}>
                  {health.isLoading ? "verificando" : isHealthy ? "operacional" : "instável"}
                </Badge>
              </div>
              <p className="text-xs text-subtle-foreground">
                A Publicação Inteligente depende da disponibilidade da Groq — se estiver fora do
                ar, publicações para 2–4 contas usam o texto original automaticamente.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
