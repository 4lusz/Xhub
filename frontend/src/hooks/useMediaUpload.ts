import { useMutation } from "@tanstack/react-query";

import { deleteMedia, uploadMedia } from "@/services/media";

/**
 * Mutations "cruas" de upload/remoção de mídia -- sem toasts de
 * sucesso/erro próprios, porque `useMediaComposer` já trata cada caso
 * (upload com preview otimista, remoção silenciosa) de forma mais
 * específica do que um toast genérico permitiria.
 */
export function useUploadMedia() {
  return useMutation({
    mutationFn: (file: File) => uploadMedia(file),
  });
}

export function useDeleteMedia() {
  return useMutation({
    mutationFn: (mediaId: string) => deleteMedia(mediaId),
  });
}
