import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Pencil, X, ZoomIn, ZoomOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import type { MediaKind } from "@/types/media";

export interface LightboxItem {
  previewUrl: string;
  mediaType: MediaKind;
  fileName: string;
}

interface MediaLightboxProps {
  items: LightboxItem[];
  index: number;
  isOpen: boolean;
  onClose: () => void;
  onIndexChange: (index: number) => void;
  onEditCurrent?: () => void;
}

const MIN_ZOOM = 1;
const MAX_ZOOM = 4;

/**
 * Ferramenta de visualização completa da mídia anexada: zoom + pan em
 * imagens/gifs, player nativo (com barra de progresso, volume e
 * fullscreen já embutidos pelo navegador) para vídeo, e navegação
 * entre os arquivos anexados ao mesmo post. Aberta ao clicar em uma
 * miniatura no `MediaComposer`.
 */
export function MediaLightbox({ items, index, isOpen, onClose, onIndexChange, onEditCurrent }: MediaLightboxProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragState = useRef<{ startX: number; startY: number; originX: number; originY: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const current = items[index];

  const resetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  useEffect(() => {
    resetView();
  }, [index, isOpen, resetView]);

  const goTo = useCallback(
    (nextIndex: number) => {
      if (nextIndex < 0 || nextIndex >= items.length) return;
      onIndexChange(nextIndex);
    },
    [items.length, onIndexChange],
  );

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft") goTo(index - 1);
      if (event.key === "ArrowRight") goTo(index + 1);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, index, goTo]);

  if (!current) return null;

  const isZoomable = current.mediaType !== "video";

  const handleWheel = (event: React.WheelEvent) => {
    if (!isZoomable) return;
    event.preventDefault();
    setZoom((z) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z - event.deltaY * 0.002)));
  };

  const handleMouseDown = (event: React.MouseEvent) => {
    if (!isZoomable || zoom <= 1) return;
    dragState.current = { startX: event.clientX, startY: event.clientY, originX: pan.x, originY: pan.y };
    setIsDragging(true);
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    if (!dragState.current) return;
    const { startX, startY, originX, originY } = dragState.current;
    setPan({ x: originX + (event.clientX - startX), y: originY + (event.clientY - startY) });
  };

  const stopDragging = () => {
    dragState.current = null;
    setIsDragging(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        hideClose
        className="flex h-[92vh] w-[95vw] max-w-5xl flex-col gap-0 overflow-hidden bg-black p-0"
      >
        <div className="flex items-center justify-between gap-2 border-b border-white/10 bg-black/80 px-4 py-2.5">
          <span className="truncate text-xs text-white/70">{current.fileName}</span>
          <div className="flex items-center gap-1">
            {isZoomable && (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="text-white hover:bg-white/10 hover:text-white"
                  onClick={() => setZoom((z) => Math.max(MIN_ZOOM, z - 0.5))}
                  aria-label="Diminuir zoom"
                >
                  <ZoomOut className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="text-white hover:bg-white/10 hover:text-white"
                  onClick={() => setZoom((z) => Math.min(MAX_ZOOM, z + 0.5))}
                  aria-label="Aumentar zoom"
                >
                  <ZoomIn className="h-4 w-4" />
                </Button>
              </>
            )}
            {onEditCurrent && current.mediaType !== "gif" && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-white hover:bg-white/10 hover:text-white"
                onClick={onEditCurrent}
                aria-label="Editar"
              >
                <Pencil className="h-4 w-4" />
              </Button>
            )}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="text-white hover:bg-white/10 hover:text-white"
              onClick={onClose}
              aria-label="Fechar"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div
          className="relative flex flex-1 items-center justify-center overflow-hidden"
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={stopDragging}
          onMouseLeave={stopDragging}
        >
          {items.length > 1 && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute left-2 z-10 text-white hover:bg-white/10 hover:text-white disabled:opacity-20"
              onClick={() => goTo(index - 1)}
              disabled={index === 0}
              aria-label="Mídia anterior"
            >
              <ChevronLeft className="h-6 w-6" />
            </Button>
          )}

          {current.mediaType === "video" ? (
            <video src={current.previewUrl} controls autoPlay className="max-h-full max-w-full" />
          ) : (
            <img
              src={current.previewUrl}
              alt={current.fileName}
              draggable={false}
              className={cn("max-h-full max-w-full select-none", isDragging ? "cursor-grabbing" : zoom > 1 ? "cursor-grab" : "")}
              style={{ transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)` }}
            />
          )}

          {items.length > 1 && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-2 z-10 text-white hover:bg-white/10 hover:text-white disabled:opacity-20"
              onClick={() => goTo(index + 1)}
              disabled={index === items.length - 1}
              aria-label="Próxima mídia"
            >
              <ChevronRight className="h-6 w-6" />
            </Button>
          )}
        </div>

        {items.length > 1 && (
          <div className="flex items-center justify-center gap-1.5 border-t border-white/10 bg-black/80 py-2.5">
            {items.map((item, itemIndex) => (
              <button
                key={item.previewUrl}
                type="button"
                onClick={() => goTo(itemIndex)}
                aria-label={`Ir para mídia ${itemIndex + 1}`}
                className={cn(
                  "h-1.5 w-6 rounded-full transition-colors",
                  itemIndex === index ? "bg-white" : "bg-white/30 hover:bg-white/50",
                )}
              />
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
