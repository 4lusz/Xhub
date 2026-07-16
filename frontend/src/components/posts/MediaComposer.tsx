import { useRef, useState } from "react";
import { AlertCircle, ImagePlus, Loader2, Pencil, Video, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ImageEditorDialog } from "@/components/posts/ImageEditorDialog";
import { MediaLightbox } from "@/components/posts/MediaLightbox";
import { VideoTrimmerDialog } from "@/components/posts/VideoTrimmerDialog";
import { cn } from "@/lib/utils";
import { formatFileSize } from "@/lib/mediaRules";
import type { ComposerMediaItem } from "@/hooks/useMediaComposer";

interface MediaComposerProps {
  items: ComposerMediaItem[];
  canAddMore: boolean;
  disabled?: boolean;
  onAddFiles: (files: FileList) => void;
  onRemoveItem: (localId: string) => void;
  onEditItem: (localId: string, editedBlob: Blob, fileName: string) => void;
}

/**
 * Anexo de mídia direto na tela de escrita do post -- mesmo princípio
 * do compositor do X: botões de imagem/vídeo logo abaixo do texto,
 * preview em grade, edição (crop/zoom/rotação para imagem, corte para
 * vídeo -- ambos 100% no navegador) e uma visualização completa em
 * tela cheia (`MediaLightbox`) para conferir o resultado antes de
 * publicar. A mídia é sempre idêntica para todas as contas
 * selecionadas; a Publicação Inteligente nunca a altera, só o texto.
 */
export function MediaComposer({
  items,
  canAddMore,
  disabled,
  onAddFiles,
  onRemoveItem,
  onEditItem,
}: MediaComposerProps) {
  const imageInputRef = useRef<HTMLInputElement>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [editingLocalId, setEditingLocalId] = useState<string | null>(null);
  const [editorSourceUrl, setEditorSourceUrl] = useState<string | null>(null);

  const handleFilesSelected = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      onAddFiles(event.target.files);
    }
    event.target.value = "";
  };

  const openEditor = (item: ComposerMediaItem) => {
    setEditingLocalId(item.localId);
    setEditorSourceUrl(URL.createObjectURL(item.originalFile));
    setLightboxIndex(null);
  };

  const closeEditor = () => {
    if (editorSourceUrl) URL.revokeObjectURL(editorSourceUrl);
    setEditingLocalId(null);
    setEditorSourceUrl(null);
  };

  const editingItem = items.find((item) => item.localId === editingLocalId) ?? null;

  const lightboxItems = items.map((item) => ({
    previewUrl: item.previewUrl,
    mediaType: item.mediaType,
    fileName: item.fileName,
  }));

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1">
        <input
          ref={imageInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          multiple
          className="hidden"
          onChange={handleFilesSelected}
        />
        <input
          ref={videoInputRef}
          type="file"
          accept="video/mp4"
          className="hidden"
          onChange={handleFilesSelected}
        />

        <Button
          type="button"
          variant="ghost"
          size="icon"
          disabled={disabled || !canAddMore}
          onClick={() => imageInputRef.current?.click()}
          aria-label="Adicionar imagem ou gif"
          title="Adicionar imagem ou gif"
        >
          <ImagePlus className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          disabled={disabled || !canAddMore}
          onClick={() => videoInputRef.current?.click()}
          aria-label="Adicionar vídeo"
          title="Adicionar vídeo"
        >
          <Video className="h-4 w-4" />
        </Button>

        {items.length > 0 && (
          <span className="text-xs text-subtle-foreground">
            {items.length}/4 arquivo{items.length > 1 ? "s" : ""}
          </span>
        )}
      </div>

      {items.length > 0 && (
        <div className={cn("grid gap-2", items.length === 1 ? "grid-cols-1" : "grid-cols-2")}>
          {items.map((item, index) => (
            <div
              key={item.localId}
              className="group relative overflow-hidden rounded-lg border border-border bg-surface"
            >
              <button
                type="button"
                className="block w-full"
                onClick={() => setLightboxIndex(index)}
                aria-label={`Ver ${item.fileName} em tamanho grande`}
              >
                {item.mediaType === "video" ? (
                  <video src={item.previewUrl} className="h-40 w-full object-cover" controls={false} muted />
                ) : (
                  <img src={item.previewUrl} alt={item.fileName} className="h-40 w-full object-cover" />
                )}
              </button>

              <div className="absolute right-1.5 top-1.5 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                {item.mediaType !== "gif" && (
                  <button
                    type="button"
                    onClick={() => openEditor(item)}
                    disabled={disabled || item.isUploading}
                    aria-label={`Editar ${item.fileName}`}
                    className="flex h-6 w-6 items-center justify-center rounded-full bg-background/80 text-foreground shadow transition-colors hover:bg-background disabled:opacity-50"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onRemoveItem(item.localId)}
                  disabled={disabled}
                  aria-label={`Remover ${item.fileName}`}
                  className="flex h-6 w-6 items-center justify-center rounded-full bg-background/80 text-foreground shadow transition-colors hover:bg-background disabled:opacity-50"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>

              {item.isUploading && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-background/60">
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                </div>
              )}

              {item.error && (
                <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center gap-1.5 bg-destructive/90 px-2 py-1 text-xs text-destructive-foreground">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{item.error}</span>
                </div>
              )}

              {!item.isUploading && !item.error && (
                <span className="pointer-events-none absolute bottom-1.5 left-1.5 rounded bg-background/80 px-1.5 py-0.5 text-[10px] text-subtle-foreground">
                  {formatFileSize(item.fileSizeBytes)}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      <MediaLightbox
        items={lightboxItems}
        index={lightboxIndex ?? 0}
        isOpen={lightboxIndex !== null}
        onClose={() => setLightboxIndex(null)}
        onIndexChange={setLightboxIndex}
        onEditCurrent={
          lightboxIndex !== null && items[lightboxIndex]?.mediaType !== "gif"
            ? () => openEditor(items[lightboxIndex])
            : undefined
        }
      />

      {editingItem && editingItem.mediaType !== "video" && editorSourceUrl && (
        <ImageEditorDialog
          isOpen
          imageSrc={editorSourceUrl}
          contentType={editingItem.originalFile.type || "image/jpeg"}
          onCancel={closeEditor}
          onApply={(blob) => {
            onEditItem(editingItem.localId, blob, editingItem.fileName);
            closeEditor();
          }}
        />
      )}

      {editingItem && editingItem.mediaType === "video" && editorSourceUrl && (
        <VideoTrimmerDialog
          isOpen
          videoSrc={editorSourceUrl}
          originalFile={editingItem.originalFile}
          onCancel={closeEditor}
          onApply={(blob) => {
            onEditItem(editingItem.localId, blob, editingItem.fileName);
            closeEditor();
          }}
        />
      )}
    </div>
  );
}
