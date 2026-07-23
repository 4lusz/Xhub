import type { PostMedia } from "@/types/media";

export type PostStatus =
  | "draft"
  | "pending"
  | "scheduled"
  | "publishing"
  | "published"
  | "failed";

export type PostAccountStatus = "pending" | "published" | "failed";

/**
 * Fluxo 1 (SHARED, comportamento histórico): um único texto original,
 * Publicação Inteligente opcional/obrigatória por faixa de contas.
 * Fluxo 2 (INDEPENDENT): sem texto principal -- cada conta escreve seu
 * próprio tweet, sem Publicação Inteligente. Ver CLAUDE.md.
 */
export type PostCompositionMode = "shared" | "independent";

export interface PostAccount {
  twitter_account_id: string;
  username: string;
  status: PostAccountStatus;
  // error_message não é exposto ao cliente — o motivo detalhado da
  // falha (resposta original da API do X) fica disponível só para o
  // administrador, ver types/admin.ts::AdminPostAccount.
  x_post_id: string | null;
  /** Texto efetivo desta conta -- sempre presente no modo independent. */
  rendered_text: string | null;
}

export interface Post {
  id: string;
  user_id: string;
  composition_mode: PostCompositionMode;
  /** `null` apenas no modo independent -- ver `accounts[].rendered_text`. */
  text: string | null;
  status: PostStatus;
  created_at: string;
  updated_at: string;
  accounts: PostAccount[];
  /** Mídia anexada -- compartilhada (post_account_id null) ou individual por conta. */
  media: PostMedia[];
}

export interface CreatePostPayload {
  composition_mode?: PostCompositionMode;
  /** Obrigatório no modo shared; ausente/vazio no modo independent. */
  text?: string | null;
  twitter_account_ids: string[];
  /** Modo shared: texto final opcional por conta (Publicação Inteligente). Modo independent: o tweet de cada conta, obrigatório para todas. */
  rendered_texts?: Record<string, string> | null;
  /** Mídia compartilhada entre todas as contas -- ids de PostMedia já enviados via POST /media/upload. */
  media_ids?: string[] | null;
  /** Mídia individual por conta (só no modo independent) -- mapa twitter_account_id -> media_ids. Mutuamente exclusivo com media_ids. */
  account_media_ids?: Record<string, string[]> | null;
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
