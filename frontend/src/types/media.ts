export type MediaKind = "image" | "gif" | "video";

export interface PostMedia {
  id: string;
  media_type: MediaKind;
  content_type: string;
  file_size_bytes: number;
  position: number | null;
  created_at: string;
}
