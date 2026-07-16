import { useMutation } from "@tanstack/react-query";

import { fetchIntelligentPublicationPreview } from "@/services/intelligentPublication";
import type { IntelligentPublicationPreviewRequest } from "@/types/intelligentPublication";

/**
 * Encapsula a chamada de preview da Publicacao Inteligente como uma
 * mutation do React Query (a chamada tem efeito colateral --
 * potencialmente aciona a Groq -- por isso `useMutation` em vez de
 * `useQuery`, seguindo a mesma biblioteca ja usada em
 * `hooks/useHealthCheck.ts`).
 *
 * Consumido por `pages/NewPostPage.tsx`, que usa `preview.mutate(...)`
 * ao clicar em "Gerar Publicação Inteligente" e passa o resultado para
 * `IntelligentPublicationPreviewModal` (isLoading/errorMessage/onRetry/
 * onConfirm ligados diretamente ao estado desta mutation).
 */
export function useIntelligentPublicationPreview() {
  return useMutation({
    mutationFn: (request: IntelligentPublicationPreviewRequest) =>
      fetchIntelligentPublicationPreview(request),
  });
}
