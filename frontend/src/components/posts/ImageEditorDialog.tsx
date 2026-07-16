import { useCallback, useEffect, useState } from "react";
import Cropper, { type Area, type MediaSize } from "react-easy-crop";
import { Check, RotateCcw, RotateCw, ZoomIn } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";
import { getCroppedImageBlob, type PixelCropArea } from "@/lib/imageCrop";

interface AspectPreset {
  label: string;
  value: number | null;
}

const ASPECT_PRESETS: AspectPreset[] = [
  { label: "Original", value: null },
  { label: "Quadrado", value: 1 },
  { label: "Retrato 4:5", value: 4 / 5 },
  { label: "Paisagem 16:9", value: 16 / 9 },
];

interface ImageEditorDialogProps {
  isOpen: boolean;
  imageSrc: string;
  contentType: string;
  onCancel: () => void;
  onApply: (blob: Blob) => void;
}

/**
 * Editor de imagem (crop + zoom + rotação) direto no navegador --
 * inteiramente client-side, sem nenhuma chamada ao backend. O
 * resultado (Blob) substitui o arquivo original antes do upload. Só
 * usado para imagens estáticas (JPEG/PNG/WEBP); GIFs animados nunca
 * abrem este editor (canvas destruiria a animação, ver
 * `lib/imageCrop.ts`).
 */
export function ImageEditorDialog({
  isOpen,
  imageSrc,
  contentType,
  onCancel,
  onApply,
}: ImageEditorDialogProps) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [aspect, setAspect] = useState<number | null>(null);
  const [naturalAspect, setNaturalAspect] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<PixelCropArea | null>(null);
  const [isApplying, setIsApplying] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setCrop({ x: 0, y: 0 });
    setZoom(1);
    setRotation(0);
    setAspect(null);
    setCroppedAreaPixels(null);
  }, [isOpen, imageSrc]);

  const handleMediaLoaded = useCallback((mediaSize: MediaSize) => {
    setNaturalAspect(mediaSize.naturalWidth / mediaSize.naturalHeight);
  }, []);

  const handleCropComplete = useCallback((_area: Area, areaPixels: Area) => {
    setCroppedAreaPixels(areaPixels);
  }, []);

  const handleApply = async () => {
    if (!croppedAreaPixels) return;
    setIsApplying(true);
    try {
      const blob = await getCroppedImageBlob(imageSrc, croppedAreaPixels, rotation, contentType);
      onApply(blob);
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Editar imagem</DialogTitle>
          <DialogDescription>
            Ajuste o recorte, o zoom e a rotação. A imagem final é gerada no seu navegador antes de
            ser enviada.
          </DialogDescription>
        </DialogHeader>

        <div className="relative h-[22rem] w-full overflow-hidden rounded-lg bg-black">
          <Cropper
            image={imageSrc}
            crop={crop}
            zoom={zoom}
            rotation={rotation}
            aspect={aspect ?? naturalAspect}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onRotationChange={setRotation}
            onCropComplete={handleCropComplete}
            onMediaLoaded={handleMediaLoaded}
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {ASPECT_PRESETS.map((preset) => (
            <Button
              key={preset.label}
              type="button"
              size="sm"
              variant={
                (preset.value === null && aspect === null) || preset.value === aspect
                  ? "secondary"
                  : "outline"
              }
              onClick={() => setAspect(preset.value)}
            >
              {preset.label}
            </Button>
          ))}
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <ZoomIn className="h-4 w-4 shrink-0 text-muted-foreground" />
            <Slider min={1} max={4} step={0.01} value={[zoom]} onValueChange={([value]) => setZoom(value)} />
          </div>
          <div className="flex items-center gap-3">
            <Button type="button" variant="outline" size="icon" onClick={() => setRotation((r) => (r - 90 + 360) % 360)}>
              <RotateCcw className="h-4 w-4" />
            </Button>
            <Slider
              min={0}
              max={359}
              step={1}
              value={[rotation]}
              onValueChange={([value]) => setRotation(value)}
            />
            <Button type="button" variant="outline" size="icon" onClick={() => setRotation((r) => (r + 90) % 360)}>
              <RotateCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel} disabled={isApplying}>
            Cancelar
          </Button>
          <Button onClick={handleApply} disabled={isApplying || !croppedAreaPixels} className={cn(isApplying && "opacity-80")}>
            <Check className="h-4 w-4" />
            {isApplying ? "Aplicando…" : "Aplicar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
