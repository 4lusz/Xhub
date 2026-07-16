import { useEffect, useMemo, useRef, useState } from "react";
import { Check, Loader2, Pause, Play, Scissors } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import { useFfmpeg } from "@/hooks/useFfmpeg";

interface VideoTrimmerDialogProps {
  isOpen: boolean;
  videoSrc: string;
  originalFile: File;
  onCancel: () => void;
  onApply: (blob: Blob) => void;
}

function formatSeconds(value: number): string {
  if (!Number.isFinite(value)) return "0:00";
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${seconds}`;
}

/**
 * Corte (trim) real de vídeo -- inteiramente no navegador via
 * ffmpeg.wasm (ver `hooks/useFfmpeg.ts`), sem processamento no
 * backend. O usuário escolhe início/fim arrastando os dois marcadores
 * (com preview ao vivo do vídeo naquele ponto); "Cortar" gera o
 * arquivo final e substitui o vídeo original antes do upload.
 */
export function VideoTrimmerDialog({
  isOpen,
  videoSrc,
  originalFile,
  onCancel,
  onApply,
}: VideoTrimmerDialogProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [duration, setDuration] = useState(0);
  const [range, setRange] = useState<[number, number]>([0, 0]);
  const [isPlaying, setIsPlaying] = useState(false);
  const { trimVideo, isLoadingCore, isTrimming, progress } = useFfmpeg();

  useEffect(() => {
    if (!isOpen) return;
    setDuration(0);
    setRange([0, 0]);
    setIsPlaying(false);
  }, [isOpen, videoSrc]);

  const handleLoadedMetadata = () => {
    const video = videoRef.current;
    if (!video) return;
    setDuration(video.duration);
    setRange([0, video.duration]);
  };

  const handleRangeChange = ([start, end]: number[]) => {
    setRange([start, end]);
    const video = videoRef.current;
    if (video) {
      video.currentTime = start;
    }
  };

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video.play();
      setIsPlaying(true);
    } else {
      video.pause();
      setIsPlaying(false);
    }
  };

  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.currentTime >= range[1]) {
      video.pause();
      video.currentTime = range[0];
      setIsPlaying(false);
    }
  };

  const trimmedDuration = useMemo(() => Math.max(0, range[1] - range[0]), [range]);
  const isProcessing = isLoadingCore || isTrimming;
  const isFullDuration = range[0] <= 0.05 && range[1] >= duration - 0.05;

  const handleApply = async () => {
    if (isFullDuration) {
      onApply(originalFile);
      return;
    }
    const blob = await trimVideo(originalFile, range[0], range[1]);
    onApply(blob);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !isProcessing && onCancel()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Cortar vídeo</DialogTitle>
          <DialogDescription>
            Arraste os marcadores para escolher o início e o fim. O corte é feito no seu navegador
            antes do envio -- o backend recebe só o resultado final.
          </DialogDescription>
        </DialogHeader>

        <div className="relative overflow-hidden rounded-lg bg-black">
          <video
            ref={videoRef}
            src={videoSrc}
            className="max-h-[22rem] w-full"
            onLoadedMetadata={handleLoadedMetadata}
            onTimeUpdate={handleTimeUpdate}
            playsInline
          />
          <button
            type="button"
            onClick={togglePlay}
            className="absolute inset-0 flex items-center justify-center bg-black/0 text-white opacity-0 transition-opacity hover:bg-black/30 hover:opacity-100"
            aria-label={isPlaying ? "Pausar" : "Reproduzir"}
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-black/60">
              {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
            </div>
          </button>
        </div>

        {duration > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-subtle-foreground">
              <span>Início: {formatSeconds(range[0])}</span>
              <span>Duração do corte: {formatSeconds(trimmedDuration)}</span>
              <span>Fim: {formatSeconds(range[1])}</span>
            </div>
            <Slider
              min={0}
              max={duration}
              step={0.1}
              minStepsBetweenThumbs={1}
              value={range}
              onValueChange={handleRangeChange}
              disabled={isProcessing}
            />
          </div>
        )}

        {isProcessing && (
          <div className="space-y-1.5">
            <p className="text-xs text-muted-foreground">
              {isLoadingCore ? "Carregando o editor de vídeo (primeira vez apenas)…" : "Cortando vídeo…"}
            </p>
            <Progress value={isLoadingCore ? 0 : progress * 100} />
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onCancel} disabled={isProcessing}>
            Cancelar
          </Button>
          <Button onClick={handleApply} disabled={isProcessing || duration === 0}>
            {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" /> : isFullDuration ? <Check className="h-4 w-4" /> : <Scissors className="h-4 w-4" />}
            {isProcessing ? "Processando…" : isFullDuration ? "Usar vídeo inteiro" : "Cortar e usar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
