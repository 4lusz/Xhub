import { api } from "@/services/api";
import type {
  IntelligentPublicationPreview,
  IntelligentPublicationPreviewRequest,
} from "@/types/intelligentPublication";

/**
 * Solicita ao backend um preview de Publicacao Inteligente
 * (`POST /intelligent-publication/preview`). Nunca cria ou publica um
 * post -- apenas retorna o texto final sugerido por conta. A
 * confirmacao/criacao do post reutiliza o service de posts existente
 * (`services/posts.ts::createPost`, chamado por `pages/NewPostPage.tsx`
 * após o usuário confirmar as variações no modal).
 */
export async function fetchIntelligentPublicationPreview(
  request: IntelligentPublicationPreviewRequest,
): Promise<IntelligentPublicationPreview> {
  const { data } = await api.post<IntelligentPublicationPreview>(
    "/intelligent-publication/preview",
    request,
  );
  return data;
}
