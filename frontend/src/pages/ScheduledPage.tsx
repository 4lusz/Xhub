import { CalendarClock } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { PostRow } from "@/components/posts/PostRow";
import { Skeleton } from "@/components/ui/skeleton";
import { useCancelScheduledPost, usePosts, useScheduledPostDetails } from "@/hooks/usePosts";
import { formatDateTime } from "@/lib/format";

export function ScheduledPage() {
  const postsQuery = usePosts("scheduled");
  const cancelSchedule = useCancelScheduledPost();

  const posts = [...(postsQuery.data ?? [])].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );

  // Busca a data/hora exata de cada agendamento via
  // GET /posts/{id}/schedule -- confiável em qualquer navegador,
  // diferente do antigo cache local.
  const scheduleDetails = useScheduledPostDetails(posts.map((post) => post.id));

  return (
    <div className="space-y-8">
      <PageHeader
        title="Agendamentos"
        description="Posts que serão publicados automaticamente no horário definido."
      />

      <div className="space-y-3">
        {postsQuery.isLoading ? (
          Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full rounded-xl" />
          ))
        ) : posts.length === 0 ? (
          <EmptyState
            icon={<CalendarClock className="h-5 w-5" />}
            title="Nenhum agendamento"
            description="Quando você agendar um post, ele aparecerá aqui até ser publicado."
          />
        ) : (
          posts.map((post, index) => {
            const detailQuery = scheduleDetails[index];
            const scheduledFor = detailQuery?.data?.scheduled_for;

            return (
              <div key={post.id} className="space-y-1.5">
                {detailQuery?.isLoading ? (
                  <Skeleton className="h-4 w-40" />
                ) : scheduledFor ? (
                  <p className="flex items-center gap-1.5 pl-1 text-xs text-primary">
                    <CalendarClock className="h-3.5 w-3.5" />
                    Agendado para {formatDateTime(scheduledFor)}
                  </p>
                ) : null}
                <PostRow
                  post={post}
                  onCancelSchedule={() => cancelSchedule.mutate(post.id)}
                  isBusy={cancelSchedule.isPending}
                />
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
