import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  cancelScheduledPost,
  createPost,
  deletePost,
  getScheduledPost,
  listPosts,
  publishPost,
  schedulePost,
} from "@/services/posts";
import { useToast } from "@/hooks/use-toast";
import type { ApiError } from "@/types/api";
import type { CreatePostPayload, PostStatus, SchedulePostPayload } from "@/types/post";

export const postsKey = (status?: PostStatus) => ["posts", status ?? "all"] as const;
export const scheduledPostKey = (postId: string) => ["posts", postId, "schedule"] as const;

export function usePosts(status?: PostStatus) {
  return useQuery({
    queryKey: postsKey(status),
    queryFn: () => listPosts({ status }),
  });
}

/**
 * Busca o `scheduled_for` de cada post em `postIds` via
 * `GET /posts/{id}/schedule` (não há endpoint em lote). Substitui o
 * cache local em `localStorage` que existia antes desse endpoint ficar
 * disponível -- agora a data vem sempre do backend, funcionando em
 * qualquer navegador/dispositivo.
 */
export function useScheduledPostDetails(postIds: string[]) {
  return useQueries({
    queries: postIds.map((postId) => ({
      queryKey: scheduledPostKey(postId),
      queryFn: () => getScheduledPost(postId),
      staleTime: 60_000,
    })),
  });
}

function useInvalidatePosts() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["posts"] });
}

export function useCreatePost() {
  const invalidate = useInvalidatePosts();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (payload: CreatePostPayload) => createPost(payload),
    onSuccess: () => {
      invalidate();
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Não foi possível criar o post", description: error.message });
    },
  });
}

export function usePublishPost() {
  const invalidate = useInvalidatePosts();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (postId: string) => publishPost(postId),
    onSuccess: (post) => {
      invalidate();
      if (post.status === "published") {
        toast({ variant: "success", title: "Publicado com sucesso" });
      } else if (post.status === "failed") {
        toast({
          variant: "destructive",
          title: "Falha ao publicar em alguma conta",
          description: "Revise o histórico para ver o que falhou.",
        });
      }
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Não foi possível publicar", description: error.message });
    },
  });
}

export function useSchedulePost() {
  const invalidate = useInvalidatePosts();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ postId, payload }: { postId: string; payload: SchedulePostPayload }) =>
      schedulePost(postId, payload),
    onSuccess: (scheduledPost) => {
      invalidate();
      queryClient.setQueryData(scheduledPostKey(scheduledPost.post_id), scheduledPost);
      toast({ variant: "success", title: "Publicação agendada" });
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Não foi possível agendar", description: error.message });
    },
  });
}

export function useCancelScheduledPost() {
  const invalidate = useInvalidatePosts();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (postId: string) => cancelScheduledPost(postId),
    onSuccess: (_data, postId) => {
      invalidate();
      queryClient.removeQueries({ queryKey: scheduledPostKey(postId) });
      toast({ title: "Agendamento cancelado" });
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Não foi possível cancelar", description: error.message });
    },
  });
}

export function useDeletePost() {
  const invalidate = useInvalidatePosts();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (postId: string) => deletePost(postId),
    onSuccess: () => {
      invalidate();
      toast({ title: "Post removido" });
    },
    onError: (error: ApiError) => {
      toast({ variant: "destructive", title: "Não foi possível remover", description: error.message });
    },
  });
}
