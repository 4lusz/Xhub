import { useQuery } from "@tanstack/react-query";

import {
  getAccountMetricsDetail,
  getPostAccountMetricsDetail,
  listPortfolioSummary,
} from "@/services/metrics";

export function usePortfolioSummary(periodDays: number) {
  return useQuery({
    queryKey: ["metrics", "portfolio", periodDays],
    queryFn: () => listPortfolioSummary(periodDays),
  });
}

export function useAccountMetricsDetail(accountId: string | null) {
  return useQuery({
    queryKey: ["metrics", "account", accountId],
    queryFn: () => getAccountMetricsDetail(accountId as string),
    enabled: accountId !== null,
  });
}

export function usePostAccountMetricsDetail(postAccountId: string | null) {
  return useQuery({
    queryKey: ["metrics", "post-account", postAccountId],
    queryFn: () => getPostAccountMetricsDetail(postAccountId as string),
    enabled: postAccountId !== null,
  });
}
