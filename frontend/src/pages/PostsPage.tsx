import { useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { PostRow } from "@/components/posts/PostRow";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDeletePost, usePosts, usePublishPost } from "@/hooks/usePosts";
import type { PostStatus } from "@/types/post";

const TABS: { value: string; label: string; status?: PostStatus }[] = [
  { value: "all", label: "Todos" },
  { value: "published", label: "Publicados", status: "published" },
  { value: "pending", label: "Pendentes", status: "pending" },
  { value: "failed", label: "Falharam", status: "failed" },
];

export function PostsPage() {
  const [tab, setTab] = useState("all");
  const status = TABS.find((t) => t.value === tab)?.status;

  const postsQuery = usePosts(status);
  const publishPost = usePublishPost();
  const deletePost = useDeletePost();

  const posts = [...(postsQuery.data ?? [])].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <div className="space-y-8">
      <PageHeader
        title="Histórico de publicações"
        description="Acompanhe o status de tudo que foi criado no XHub."
        actions={
          <Button asChild>
            <Link to="/posts/new">
              <Sparkles className="h-4 w-4" />
              Novo post
            </Link>
          </Button>
        }
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          {TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="space-y-3">
        {postsQuery.isLoading ? (
          Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full rounded-xl" />
          ))
        ) : posts.length === 0 ? (
          <EmptyState
            icon={<Sparkles className="h-5 w-5" />}
            title="Nenhum post encontrado"
            description="Posts criados no XHub aparecem aqui, com o status de cada publicação."
            action={
              <Button asChild size="sm">
                <Link to="/posts/new">Criar post</Link>
              </Button>
            }
          />
        ) : (
          posts.map((post) => (
            <PostRow
              key={post.id}
              post={post}
              onPublish={
                post.status === "pending" || post.status === "failed"
                  ? () => publishPost.mutate(post.id)
                  : undefined
              }
              onDelete={
                // Espelha a regra do backend (`PostService.delete_post`):
                // um post com falha PARCIAL (`status === "failed"`) pode
                // ter algumas contas já `published` -- checar apenas o
                // status agregado escondia o botão de excluir só quando
                // TODAS as contas tinham sucesso, deixando visível para
                // um caso que o backend agora recusa (409).
                post.accounts.every((account) => account.status !== "published")
                  ? () => deletePost.mutate(post.id)
                  : undefined
              }
              isBusy={publishPost.isPending || deletePost.isPending}
            />
          ))
        )}
      </div>
    </div>
  );
}
