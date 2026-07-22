import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, BarChart3, Minus, TrendingDown, TrendingUp } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usePortfolioSummary } from "@/hooks/useMetrics";
import { formatCompactNumber, formatPercent, initialsFromName } from "@/lib/format";
import type { AccountPortfolioSummary } from "@/types/metrics";

const PERIOD_OPTIONS = [
  { value: "7", label: "7 dias" },
  { value: "30", label: "30 dias" },
];

function TrendBadge({ value }: { value: number | null }) {
  if (value === null) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-subtle-foreground">
        <Minus className="h-3 w-3" />—
      </span>
    );
  }

  const isUp = value > 0;
  const isFlat = value === 0;

  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium ${
        isFlat ? "text-muted-foreground" : isUp ? "text-success" : "text-destructive"
      }`}
    >
      {isFlat ? <Minus className="h-3 w-3" /> : isUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
      {formatPercent(value)}
    </span>
  );
}

function AccountRow({ account, onOpen }: { account: AccountPortfolioSummary; onOpen: () => void }) {
  return (
    <TableRow className="cursor-pointer" onClick={onOpen}>
      <TableCell>
        <div className="flex items-center gap-3">
          <Avatar className="h-9 w-9 border border-border">
            <AvatarImage src={account.profile_image_url ?? undefined} alt={account.display_name} />
            <AvatarFallback>{initialsFromName(account.display_name)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-foreground">@{account.username}</p>
            <p className="truncate text-xs text-subtle-foreground">{account.display_name}</p>
          </div>
          {account.has_anomaly && (
            <Badge variant="destructive" className="ml-1 shrink-0">
              <AlertTriangle className="h-3 w-3" />
              Alcance caiu
            </Badge>
          )}
        </div>
      </TableCell>
      <TableCell>
        <p className="text-sm text-foreground">{formatCompactNumber(account.followers_count)}</p>
        <TrendBadge value={account.followers_trend} />
      </TableCell>
      <TableCell>
        <p className="text-sm text-foreground">{formatCompactNumber(account.impressions)}</p>
        <TrendBadge value={account.impressions_trend} />
      </TableCell>
      <TableCell className="text-sm text-muted-foreground">{formatCompactNumber(account.likes)}</TableCell>
      <TableCell className="text-sm text-muted-foreground">{formatCompactNumber(account.replies)}</TableCell>
      <TableCell className="text-sm text-muted-foreground">{formatCompactNumber(account.reposts)}</TableCell>
    </TableRow>
  );
}

export function ResultsPage() {
  const navigate = useNavigate();
  const [periodDays, setPeriodDays] = useState(7);

  const { data, isLoading } = usePortfolioSummary(periodDays);
  const accounts = data ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Resultados"
        description="Desempenho de cada conta conectada — impressões, curtidas e seguidores, atualizados periodicamente pela API do X."
      />

      <Tabs value={String(periodDays)} onValueChange={(value) => setPeriodDays(Number(value))}>
        <TabsList>
          {PERIOD_OPTIONS.map((option) => (
            <TabsTrigger key={option.value} value={option.value}>
              {option.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      ) : accounts.length === 0 ? (
        <EmptyState
          icon={<BarChart3 className="h-5 w-5" />}
          title="Ainda sem dados de desempenho"
          description="Assim que suas contas conectadas tiverem posts publicados, as métricas aparecem aqui automaticamente — a coleta roda periodicamente em segundo plano."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Conta</TableHead>
                <TableHead>Seguidores</TableHead>
                <TableHead>Impressões</TableHead>
                <TableHead>Curtidas</TableHead>
                <TableHead>Respostas</TableHead>
                <TableHead>Republicações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.map((account) => (
                <AccountRow
                  key={account.twitter_account_id}
                  account={account}
                  onOpen={() => navigate(`/results/${account.twitter_account_id}`)}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
