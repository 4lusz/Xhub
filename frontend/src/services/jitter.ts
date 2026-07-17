import { api } from "@/services/api";
import type { JitterSettings, UpdateJitterSettingsPayload } from "@/types/jitter";

export async function getJitterSettings(): Promise<JitterSettings> {
  const { data } = await api.get<JitterSettings>("/admin/jitter-settings");
  return data;
}

export async function updateJitterSettings(
  payload: UpdateJitterSettingsPayload,
): Promise<JitterSettings> {
  const { data } = await api.patch<JitterSettings>("/admin/jitter-settings", payload);
  return data;
}
