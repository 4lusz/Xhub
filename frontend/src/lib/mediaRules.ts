/**
 * Espelha `backend/app/domain/media_rules.py` para dar feedback
 * instantâneo no navegador (arquivo não suportado, tamanho excedido,
 * combinação inválida) antes de gastar uma chamada de upload. O
 * backend é sempre a fonte da verdade -- esta validação é só UX,
 * nunca a única linha de defesa.
 */
import type { MediaKind } from "@/types/media";

export const MAX_MEDIA_PER_POST = 4;

const ALLOWED_CONTENT_TYPES: Record<string, MediaKind> = {
  "image/jpeg": "image",
  "image/png": "image",
  "image/webp": "image",
  "image/gif": "gif",
  "video/mp4": "video",
};

const MAX_SIZE_BYTES_BY_KIND: Record<MediaKind, number> = {
  image: 5 * 1024 * 1024,
  gif: 15 * 1024 * 1024,
  video: 512 * 1024 * 1024,
};

export function classifyFile(file: File): MediaKind | null {
  return ALLOWED_CONTENT_TYPES[file.type.toLowerCase()] ?? null;
}

export function maxSizeBytesFor(kind: MediaKind): number {
  return MAX_SIZE_BYTES_BY_KIND[kind];
}

export function validateMediaCombination(kinds: MediaKind[]): string | null {
  if (kinds.length === 0) return null;

  if (kinds.length > MAX_MEDIA_PER_POST) {
    return `Você pode anexar no máximo ${MAX_MEDIA_PER_POST} arquivos de mídia.`;
  }

  const hasVideo = kinds.includes("video");
  const hasGif = kinds.includes("gif");

  if (hasVideo && kinds.length > 1) {
    return "Um vídeo não pode ser combinado com outras imagens ou gifs no mesmo post.";
  }

  if (hasGif && kinds.length > 1) {
    return "Um GIF não pode ser combinado com outras imagens ou vídeos no mesmo post.";
  }

  return null;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
