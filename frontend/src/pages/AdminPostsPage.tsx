import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, FileText, Search } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { PostStatusBadge } from "@/components/posts/PostStatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { useAdminPosts } from "@/hooks/useAdminPosts";
import { formatDateTime } from "@/lib/format";
import type { PostStatus } from "@/types/post";

const PAGE_SIZE = 50;

const TABS: { value: string; label: string; status?: PostStatus }[] = [
  { value: "failed", label: "Falharam", status: "failed" },
  { value: "all", label: "Todos" },
  { value: "published", label: "Publicados", status: "published" },
  { value: "pending", label: "Pendentes", status: "pending" },
  { value: "scheduled", label: "Agendados", status: "scheduled" },
];

const ACCOUNT_STATUS_LABEL: Record<string, string> = {
  pending: "Pendente",
  published: "Publicado",
  failed: "Falhou",
};

/**
 * Auditoria de publicações (`GET /admin/posts`): posts de todos os
 * usuários com o motivo exato de falha por conta, vindo direto da
 * resposta original da API do X (`PostAccount.error_message`, enriquecido
 * em `XOAuthClient.publish_post`). Só disponível aqui -- o cliente não
 * vê esse detalhe técnico em `/posts` (ver `types/post.ts::PostAccount`).
 *
 * Privacidade: o conteúdo do post (texto) nunca é exposto nesta tela --
 * nem o backend retorna esse campo aqui (ver `AdminPostResponse`). O
 * admin vê apenas status (do post e por conta do X) e o motivo técnico
 * de falha, nunca o que foi escrito.
 */
export function AdminPostsPage() {
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";

  // Chegando com `?q=` (ex.: botão "Posts" na tela de Usuários), mostra
  // todos os status daquele usuário -- filtrar só por "failed" junto com
  // uma busca específica esconderia posts relevantes sem falha.
  const [tab, setTab] = useState(initialQuery ? "all" : "failed");
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState(initialQuery);
  const status = TABS.find((t) => t.value === tab)?.status;

  const { data, isLoading, isPlaceholderData } = useAdminPosts(status, page, PAGE_SIZE);

  const posts = data ?? [];
  const hasNextPage = posts.length === PAGE_SIZE;

  // Filtro por conta/usuário aplicado sobre a página atual -- permite
  // localizar rapidamente "os posts de uma conta" específica (@usuário
  // do X, nome ou e-mail do dono) sem precisar de um endpoint novo.
  const filteredPosts = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return posts;
    return posts.filter(
      (post) =>
        post.user_name.toLowerCase().includes(query) ||
        post.user_email.toLowerCase().includes(query) ||
        post.accounts.some((account) => account.username.toLowerCase().includes(query)),
    );
  }, [posts, search]);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Publicações"
        description="Status de publicação de todos os usuários, com o motivo exato de falha retornado pela API do X — para auditoria e suporte. O conteúdo dos posts não é exibido aqui."
      />

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Tabs
          value={tab}
          onValueChange={(value) => {
            setTab(value);
            setPage(0);
          }}
        >
          <TabsList>
            {TABS.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <div className="relative w-full sm:w-64">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por conta, nome ou e-mail"
            className="pl-9"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      ) : filteredPosts.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-5 w-5" />}
          title="Nenhum post encontrado"
          description={
            search.trim()
              ? "Nenhum resultado para essa busca nesta página."
              : tab === "failed"
                ? "Nenhuma publicação com falha registrada."
                : "Nenhum post nesta categoria."
          }
        />
      ) : (
        <div className="space-y-4">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="whitespace-nowrap">Data/hora</TableHead>
                  <TableHead>Usuário</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Contas / motivo da falha</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPosts.map((post) => (
                  <TableRow key={post.id}>
                    <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                      {formatDateTime(post.created_at)}
                    </TableCell>
                    <TableCell className="text-sm">
                      <p className="font-medium text-foreground">{post.user_name}</p>
                      <p className="text-xs text-muted-foreground">{post.user_email}</p>
                    </TableCell>
                    <TableCell>
                      <PostStatusBadge status={post.status} />
                    </TableCell>
                    <TableCell className="min-w-[260px] max-w-md">
                      <div className="space-y-1.5">
                        {post.accounts.map((account) => (
                          <div key={account.twitter_account_id} className="text-xs">
                            <div className="flex items-center gap-1.5">
                              <Badge
                                variant={
                                  account.status === "published"
                                    ? "success"
                                    : account.status === "failed"
                                      ? "destructive"
                                      : "secondary"
                                }
                              >
                                @{account.username} · {ACCOUNT_STATUS_LABEL[account.status]}
                              </Badge>
                            </div>
                            {account.status === "failed" && account.error_message && (
                              <p className="mt-0.5 pl-1 text-destructive">
                                {account.error_message}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
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
