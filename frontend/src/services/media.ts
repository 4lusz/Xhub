import { api } from "@/services/api";
import type { PostMedia } from "@/types/media";

export async function uploadMedia(file: File): Promise<PostMedia> {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await api.post<PostMedia>("/media/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteMedia(mediaId: string): Promise<void> {
  await api.delete(`/media/${mediaId}`);
}
