import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { listAdminPosts } from "@/services/admin";

export const adminPostsKey = (status: string | undefined, page: number, pageSize: number) =>
  ["admin", "posts", status ?? "all", page, pageSize] as const;

/**
 * Posts de todos os usuários com o motivo exato de falha por conta
 * (`GET /admin/posts`). Mesmo padrão de paginação "anterior/próxima" de
 * `useAuditLogs` -- o backend não expõe contagem total.
 */
export function useAdminPosts(status: string | undefined, page: number, pageSize = 50) {
  return useQuery({
    queryKey: adminPostsKey(status, page, pageSize),
    queryFn: () => listAdminPosts({ status, offset: page * pageSize, limit: pageSize }),
    placeholderData: keepPreviousData,
    staleTime: 15_000,
  });
}
