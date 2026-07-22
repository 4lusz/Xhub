import { api } from "@/services/api";
import type {
  AccountMetricsDetail,
  AccountPortfolioSummary,
  PostAccountMetricsDetail,
} from "@/types/metrics";

export async function listPortfolioSummary(periodDays: number): Promise<AccountPortfolioSummary[]> {
  const { data } = await api.get<AccountPortfolioSummary[]>("/metrics/accounts", {
    params: { period_days: periodDays },
  });
  return data;
}

export async function getAccountMetricsDetail(accountId: string): Promise<AccountMetricsDetail> {
  const { data } = await api.get<AccountMetricsDetail>(`/metrics/accounts/${accountId}`);
  return data;
}

export async function getPostAccountMetricsDetail(
  postAccountId: string,
): Promise<PostAccountMetricsDetail> {
  const { data } = await api.get<PostAccountMetricsDetail>(`/metrics/post-accounts/${postAccountId}`);
  return data;
}
