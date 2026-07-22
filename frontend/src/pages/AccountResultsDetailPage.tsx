import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, FileText } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAccountMetricsDetail, usePostAccountMetricsDetail } from "@/hooks/useMetrics";
import { formatCompactNumber, formatDate, formatDateTime } from "@/lib/format";

function PostHistoryDialog({
  postAccountId,
  onClose,
}: {
  postAccountId: string | null;
  onClose: () => void;
}) {
  const { data, isLoading } = usePostAccountMetricsDetail(postAccountId);

  return (
    <Dialog open={postAccountId !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{data ? `Desempenho de @${data.username}` : "Desempenho do post"}</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : !data || data.history.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-5 w-5" />}
            title="Ainda sem métricas coletadas"
            description="A primeira coleta deste post ainda não aconteceu — ela roda periodicamente em segundo plano."
          />
        ) : (
          <div className="max-h-96 overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Coletado em</TableHead>
                  <TableHead>Impressões</TableHead>
                  <TableHead>Curtidas</TableHead>
                  <TableHead>Respostas</TableHead>
                  <TableHead>Republicações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.history.map((point, index) => (
                  <TableRow key={index}>
                    <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                      {formatDateTime(point.collected_at)}
                    </TableCell>
                    <TableCell className="text-sm">{formatCompactNumber(point.impression_count)}</TableCell>
                    <TableCell className="text-sm">{formatCompactNumber(point.like_count)}</TableCell>
                    <TableCell className="text-sm">{formatCompactNumber(point.reply_count)}</TableCell>
                    <TableCell className="text-sm">{formatCompactNumber(point.repost_count)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function AccountResultsDetailPage() {
  const { accountId } = useParams<{ accountId: string }>();
  const navigate = useNavigate();
  const [selectedPostAccountId, setSelectedPostAccountId] = useState<string | null>(null);

  const { data, isLoading } = useAccountMetricsDetail(accountId ?? null);

  return (
    <div className="space-y-8">
      <PageHeader
        title={data ? `@${data.username}` : "Resultados da conta"}
        description={data?.display_name ?? "Histórico de desempenho desta conta."}
        actions={
          <Button variant="ghost" size="sm" onClick={() => navigate("/results")}>
            <ArrowLeft className="h-4 w-4" />
            Voltar
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Seguidores ao longo do tempo</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-8 w-full" />
                ))}
              </div>
            ) : !data || data.followers_history.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Ainda sem histórico suficiente — a coleta roda periodicamente em segundo plano.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {data.followers_history
                  .slice()
                  .reverse()
                  .slice(0, 15)
                  .map((point, index) => (
                    <li key={index} className="flex items-center justify-between py-2 text-sm">
                      <span className="text-muted-foreground">{formatDate(point.collected_at)}</span>
                      <span className="font-medium text-foreground">
                        {formatCompactNumber(point.followers_count)}
                      </span>
                    </li>
                  ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Melhores posts</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-14 w-full" />
                ))}
              </div>
            ) : !data || data.top_posts.length === 0 ? (
              <EmptyState
                icon={<FileText className="h-5 w-5" />}
                title="Nenhum post publicado ainda"
              />
            ) : (
              <ul className="divide-y divide-border">
                {data.top_posts.map((post) => (
                  <li key={post.post_account_id}>
                    <button
                      type="button"
                      onClick={() => setSelectedPostAccountId(post.post_account_id)}
                      className="flex w-full items-center justify-between gap-4 py-3 text-left transition-colors hover:bg-surface-hover"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm text-foreground">{post.text_preview}</p>
                        <p className="text-xs text-subtle-foreground">
                          {formatDateTime(post.published_at)}
                        </p>
                      </div>
                      <span className="shrink-0 text-sm font-medium text-foreground">
                        {formatCompactNumber(post.impression_count)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <PostHistoryDialog
        postAccountId={selectedPostAccountId}
        onClose={() => setSelectedPostAccountId(null)}
      />
    </div>
  );
}
