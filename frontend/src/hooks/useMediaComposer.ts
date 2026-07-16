import { useCallback, useEffect, useRef, useState } from "react";

import { useDeleteMedia, useUploadMedia } from "@/hooks/useMediaUpload";
import { useToast } from "@/hooks/use-toast";
import {
  MAX_MEDIA_PER_POST,
  classifyFile,
  maxSizeBytesFor,
  validateMediaCombination,
} from "@/lib/mediaRules";
import type { ApiError } from "@/types/api";
import type { MediaKind, PostMedia } from "@/types/media";

export interface ComposerMediaItem {
  localId: string;
  /** Arquivo original selecionado pelo usuário -- nunca sobrescrito, mesmo após editar. Reeditar sempre parte daqui (evita degradar qualidade a cada edição sucessiva). */
  originalFile: File;
  previewUrl: string;
  mediaType: MediaKind;
  fileName: string;
  fileSizeBytes: number;
  media: PostMedia | null;
  isUploading: boolean;
  error: string | null;
}

/**
 * Estado do compositor de mídia da tela de novo post (ver
 * `components/posts/MediaComposer.tsx`). O preview usa
 * `URL.createObjectURL(file)` -- local, instantâneo, sem round-trip ao
 * backend -- enquanto o upload real (`POST /media/upload`) roda em
 * paralelo; o item só fica "pronto para publicar" (contribui para
 * `mediaIds`) quando o upload confirma. Remover um item já enviado
 * dispara a remoção no backend (`DELETE /media/{id}`); a mídia nunca é
 * alterada pela Publicação Inteligente, que atua apenas sobre o texto.
 *
 * Edição (crop/zoom/rotação de imagem, corte de vídeo -- ver
 * `components/posts/ImageEditorDialog.tsx`/`VideoTrimmerDialog.tsx`)
 * roda 100% no navegador; `editItem` troca o arquivo enviado ao
 * backend (apaga o upload antigo, envia o novo) mas preserva
 * `originalFile` intacto.
 */
export function useMediaComposer() {
  const [items, setItems] = useState<ComposerMediaItem[]>([]);
  const itemsRef = useRef(items);
  itemsRef.current = items;

  const uploadMedia = useUploadMedia();
  const deleteMedia = useDeleteMedia();
  const { toast } = useToast();

  useEffect(
    () => () => {
      itemsRef.current.forEach((item) => URL.revokeObjectURL(item.previewUrl));
    },
    [],
  );

  const uploadForItem = useCallback(
    (localId: string, file: File) => {
      setItems((current) =>
        current.map((item) => (item.localId === localId ? { ...item, isUploading: true, error: null } : item)),
      );

      uploadMedia.mutate(file, {
        onSuccess: (media) => {
          setItems((current) =>
            current.map((item) => (item.localId === localId ? { ...item, media, isUploading: false } : item)),
          );
        },
        onError: (error) => {
          const message = (error as ApiError).message ?? "Falha ao enviar o arquivo.";
          setItems((current) =>
            current.map((item) =>
              item.localId === localId ? { ...item, isUploading: false, error: message } : item,
            ),
          );
        },
      });
    },
    [uploadMedia],
  );

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      const incoming = Array.from(files);
      const projectedKinds = itemsRef.current.map((item) => item.mediaType);

      for (const file of incoming) {
        const kind = classifyFile(file);

        if (!kind) {
          toast({
            variant: "destructive",
            title: "Arquivo não suportado",
            description: `${file.name}: envie uma imagem (JPEG, PNG ou WEBP), um GIF ou um vídeo MP4.`,
          });
          continue;
        }

        if (file.size > maxSizeBytesFor(kind)) {
          toast({
            variant: "destructive",
            title: "Arquivo muito grande",
            description: `${file.name} excede o tamanho máximo permitido para este tipo de mídia.`,
          });
          continue;
        }

        const combinationError = validateMediaCombination([...projectedKinds, kind]);
        if (combinationError) {
          toast({ variant: "destructive", title: "Combinação de mídia inválida", description: combinationError });
          continue;
        }
        projectedKinds.push(kind);

        const localId = crypto.randomUUID();
        const previewUrl = URL.createObjectURL(file);

        setItems((current) => [
          ...current,
          {
            localId,
            originalFile: file,
            previewUrl,
            mediaType: kind,
            fileName: file.name,
            fileSizeBytes: file.size,
            media: null,
            isUploading: true,
            error: null,
          },
        ]);

        uploadForItem(localId, file);
      }
    },
    [toast, uploadForItem],
  );

  const removeItem = useCallback(
    (localId: string) => {
      const target = itemsRef.current.find((item) => item.localId === localId);
      if (!target) return;

      URL.revokeObjectURL(target.previewUrl);
      if (target.media) {
        deleteMedia.mutate(target.media.id);
      }
      setItems((current) => current.filter((item) => item.localId !== localId));
    },
    [deleteMedia],
  );

  /**
   * Substitui o arquivo de um item já existente pelo resultado de uma
   * edição (crop/rotação de imagem ou corte de vídeo), preservando a
   * posição no post. Remove o upload antigo do backend (se já
   * concluído) e envia o novo arquivo.
   */
  const editItem = useCallback(
    (localId: string, editedBlob: Blob, fileName: string) => {
      const target = itemsRef.current.find((item) => item.localId === localId);
      if (!target) return;

      const previousMediaId = target.media?.id ?? null;
      const newFile = new File([editedBlob], fileName, { type: editedBlob.type });
      const newPreviewUrl = URL.createObjectURL(newFile);

      URL.revokeObjectURL(target.previewUrl);
      setItems((current) =>
        current.map((item) =>
          item.localId === localId
            ? {
                ...item,
                previewUrl: newPreviewUrl,
                fileSizeBytes: newFile.size,
                media: null,
                isUploading: true,
                error: null,
              }
            : item,
        ),
      );

      if (previousMediaId) {
        deleteMedia.mutate(previousMediaId);
      }

      uploadForItem(localId, newFile);
    },
    [deleteMedia, uploadForItem],
  );

  const reset = useCallback(() => {
    itemsRef.current.forEach((item) => URL.revokeObjectURL(item.previewUrl));
    setItems([]);
  }, []);

  const mediaIds = items.filter((item) => item.media).map((item) => item.media!.id);
  const isUploading = items.some((item) => item.isUploading);
  const hasErrors = items.some((item) => item.error);
  const hasNonImage = items.some((item) => item.mediaType !== "image");
  const canAddMore = items.length === 0 || (!hasNonImage && items.length < MAX_MEDIA_PER_POST);

  return { items, addFiles, removeItem, editItem, reset, mediaIds, isUploading, hasErrors, canAddMore };
}
