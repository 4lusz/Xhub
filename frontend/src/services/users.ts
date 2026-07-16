import { api } from "@/services/api";
import type { CreateUserPayload, ResetPasswordResult, User, UserRole } from "@/types/user";

export async function listUsers(params?: { offset?: number; limit?: number }): Promise<User[]> {
  const { data } = await api.get<User[]>("/admin/users", {
    params: { offset: params?.offset ?? 0, limit: params?.limit ?? 100 },
  });
  return data;
}

export async function getUser(userId: string): Promise<User> {
  const { data } = await api.get<User>(`/admin/users/${userId}`);
  return data;
}

export async function createUser(payload: CreateUserPayload): Promise<User> {
  const { data } = await api.post<User>("/admin/users", payload);
  return data;
}

export async function blockUser(userId: string): Promise<User> {
  const { data } = await api.post<User>(`/admin/users/${userId}/block`);
  return data;
}

export async function unblockUser(userId: string): Promise<User> {
  const { data } = await api.post<User>(`/admin/users/${userId}/unblock`);
  return data;
}

export async function changeUserRole(userId: string, role: UserRole): Promise<User> {
  const { data } = await api.patch<User>(`/admin/users/${userId}/role`, { role });
  return data;
}

/**
 * Redefinição administrativa de senha (ver
 * docs/ROADMAP_PRIMEIRO_ACESSO.md): gera uma nova senha temporária e
 * devolve o usuário ao fluxo de primeiro acesso obrigatório.
 */
export async function resetUserPassword(userId: string): Promise<ResetPasswordResult> {
  const { data } = await api.post<ResetPasswordResult>(`/admin/users/${userId}/reset-password`);
  return data;
}
