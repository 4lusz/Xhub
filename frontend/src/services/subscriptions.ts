import { api } from "@/services/api";
import type {
  ExtraPostsPayload,
  MySubscription,
  RenewSubscriptionPayload,
  Subscription,
} from "@/types/plan";

/**
 * Assinatura do próprio usuário autenticado (`GET /me/subscription`).
 * Endpoint de cliente — não exige papel de admin, descobre a assinatura
 * a partir do token.
 */
export async function getMySubscription(): Promise<MySubscription> {
  const { data } = await api.get<MySubscription>("/me/subscription");
  return data;
}

export async function getSubscription(subscriptionId: string): Promise<Subscription> {
  const { data } = await api.get<Subscription>(`/admin/subscriptions/${subscriptionId}`);
  return data;
}

export async function getUserSubscription(userId: string): Promise<Subscription> {
  const { data } = await api.get<Subscription>(`/admin/users/${userId}/subscription`);
  return data;
}

export async function renewSubscription(
  subscriptionId: string,
  payload: RenewSubscriptionPayload,
): Promise<Subscription> {
  const { data } = await api.post<Subscription>(
    `/admin/subscriptions/${subscriptionId}/renew`,
    payload,
  );
  return data;
}

export async function blockSubscription(subscriptionId: string): Promise<Subscription> {
  const { data } = await api.post<Subscription>(
    `/admin/subscriptions/${subscriptionId}/block`,
  );
  return data;
}

export async function expireSubscription(subscriptionId: string): Promise<Subscription> {
  const { data } = await api.post<Subscription>(
    `/admin/subscriptions/${subscriptionId}/expire`,
  );
  return data;
}

export async function addExtraPosts(
  subscriptionId: string,
  payload: ExtraPostsPayload,
): Promise<Subscription> {
  const { data } = await api.post<Subscription>(
    `/admin/subscriptions/${subscriptionId}/extra-posts/add`,
    payload,
  );
  return data;
}

export async function removeExtraPosts(
  subscriptionId: string,
  payload: ExtraPostsPayload,
): Promise<Subscription> {
  const { data } = await api.post<Subscription>(
    `/admin/subscriptions/${subscriptionId}/extra-posts/remove`,
    payload,
  );
  return data;
}
