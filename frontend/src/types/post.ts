import type { PostMedia } from "@/types/media";

export type PostStatus =
  | "draft"
  | "pending"
  | "scheduled"
  | "publishing"
  | "published"
  | "failed";

export type PostAccountStatus = "pending" | "published" | "failed";

export interface PostAccount {
  twitter_account_id: string;
  username: string;
  status: PostAccountStatus;
  // error_message não é exposto ao cliente — o motivo detalhado da
  // falha (resposta original da API do X) fica disponível só para o
  // administrador, ver types/admin.ts::AdminPostAccount.
  x_post_id: string | null;
}

export interface Post {
  id: string;
  user_id: string;
  text: string;
  status: PostStatus;
  created_at: string;
  updated_at: string;
  accounts: PostAccount[];
  /** Mídia anexada -- idêntica para todas as contas, nunca alterada pela Publicação Inteligente. */
  media: PostMedia[];
}

export interface CreatePostPayload {
  text: string;
  twitter_account_ids: string[];
  /** Publicação Inteligente: texto final por conta (id -> texto). */
  rendered_texts?: Record<string, string> | null;
  /** Ids de PostMedia já enviados via POST /media/upload, na ordem de publicação. */
  media_ids?: string[] | null;
}

export interface ScheduledPost {
  id: string;
  post_id: string;
  scheduled_for: string;
  executed: boolean;
  attempts: number;
  last_error: string | null;
}

export interface SchedulePostPayload {
  scheduled_for: string;
}
