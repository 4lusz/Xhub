/**
 * Tipos da Publicacao Inteligente.
 *
 * Espelham exatamente os schemas Pydantic em
 * `backend/app/schemas/intelligent_publication.py` -- os nomes de
 * campo permanecem em snake_case de proposito, pois o restante do
 * frontend (ver `types/health.ts`) ainda nao possui uma camada de
 * conversao de casing entre API e UI.
 */

export type IntelligentPublicationStrategy =
  | "original"
  | "optional_variation"
  | "mandatory_variation";

export interface AccountPreview {
  twitter_account_id: string;
  username: string;
  display_name: string;
  text: string;
  is_variation: boolean;
  char_count: number;
  is_duplicate: boolean;
  is_valid: boolean;
}

export interface IntelligentPublicationPreview {
  original_text: string;
  strategy: IntelligentPublicationStrategy;
  is_variation_required: boolean;
  is_variation_applied: boolean;
  cache_hit: boolean;
  warning: string | null;
  model: string | null;
  prompt_version: string;
  accounts: AccountPreview[];
}

export interface IntelligentPublicationPreviewRequest {
  text: string;
  twitter_account_ids: string[];
  /**
   * Relevante apenas para 2-4 contas (estado do botao "Publicacao
   * Inteligente" no frontend, ativado por padrao). Ignorado pelo
   * backend para 1 conta (nunca aplica) e para 5+ contas (sempre
   * obrigatorio).
   */
  apply_variation?: boolean;
}
