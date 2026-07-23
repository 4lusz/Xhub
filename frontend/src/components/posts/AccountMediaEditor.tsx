import { useEffect } from "react";

import { MediaComposer } from "@/components/posts/MediaComposer";
import { useMediaComposer } from "@/hooks/useMediaComposer";

export interface AccountMediaState {
  mediaIds: string[];
  isUploading: boolean;
  hasErrors: boolean;
}

interface AccountMediaEditorProps {
  accountId: string;
  onChange: (accountId: string, state: AccountMediaState) => void;
}

/**
 * Mídia exclusiva de UMA conta, no modo "conteúdo diferente para cada
 * conta" com mídia individualizada (ver `IndependentPostComposer`) --
 * uma instância própria de `useMediaComposer` por conta, exatamente as
 * mesmas regras de validação da mídia compartilhada (mesmo componente
 * `MediaComposer`). Reporta seu estado para o pai a cada mudança, já
 * que múltiplas instâncias deste hook não podem viver num único
 * componente pai (contagem de contas é dinâmica).
 */
export function AccountMediaEditor({ accountId, onChange }: AccountMediaEditorProps) {
  const media = useMediaComposer();
  const mediaIdsKey = media.mediaIds.join(",");

  useEffect(() => {
    onChange(accountId, {
      mediaIds: media.mediaIds,
      isUploading: media.isUploading,
      hasErrors: media.hasErrors,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId, mediaIdsKey, media.isUploading, media.hasErrors]);

  return (
    <MediaComposer
      items={media.items}
      canAddMore={media.canAddMore}
      onAddFiles={media.addFiles}
      onRemoveItem={media.removeItem}
      onEditItem={media.editItem}
    />
  );
}
