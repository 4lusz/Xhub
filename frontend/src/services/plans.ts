import { api } from "@/services/api";
import type { Plan, UpdatePlanPayload } from "@/types/plan";

export async function listPlans(): Promise<Plan[]> {
  const { data } = await api.get<Plan[]>("/admin/plans");
  return data;
}

export async function syncPlans(): Promise<Plan[]> {
  const { data } = await api.post<Plan[]>("/admin/plans/sync");
  return data;
}

export async function updatePlan(planId: string, payload: UpdatePlanPayload): Promise<Plan> {
  const { data } = await api.patch<Plan>(`/admin/plans/${planId}`, payload);
  return data;
}
