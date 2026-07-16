import { useCallback, useState } from "react";
import { FFmpeg } from "@ffmpeg/ffmpeg";
import { fetchFile, toBlobURL } from "@ffmpeg/util";

/**
 * Corte (trim) real de vídeo, inteiramente no navegador, via
 * ffmpeg.wasm -- sem nenhum processamento no backend (decisão
 * explícita do usuário: o backend só recebe o arquivo final já
 * cortado). O core (`ffmpeg-core.js`/`.wasm`, ~30MB) é self-hosted em
 * `public/ffmpeg/` (ver `scripts/copy-ffmpeg-core.mjs`) -- nunca
 * carregado de um CDN de terceiros, e só baixado na primeira vez que o
 * usuário realmente abre o editor de vídeo (não no carregamento da
 * página).
 *
 * Usa `-c copy` (remux sem recodificar) em vez de recodificar
 * vídeo/áudio: muito mais rápido (segundos, não minutos, mesmo para
 * arquivos grandes) e não exige um encoder de vídeo no core reduzido
 * do ffmpeg.wasm. Contrapartida conhecida: o corte encaixa no
 * keyframe mais próximo do ponto pedido, podendo variar por até ~1-2s
 * dependendo do vídeo -- aceitável para recorte de anúncios/posts,
 * documentado aqui para não ser confundido com um bug.
 */

let ffmpegSingleton: FFmpeg | null = null;
let loadPromise: Promise<FFmpeg> | null = null;

async function getFFmpeg(): Promise<FFmpeg> {
  if (ffmpegSingleton) return ffmpegSingleton;

  if (!loadPromise) {
    loadPromise = (async () => {
      const instance = new FFmpeg();
      const baseURL = "/ffmpeg";
      await instance.load({
        coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, "text/javascript"),
        wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, "application/wasm"),
      });
      ffmpegSingleton = instance;
      return instance;
    })();
  }

  return loadPromise;
}

function extensionFromFile(file: File): string {
  const match = /\.[a-zA-Z0-9]+$/.exec(file.name);
  return match ? match[0] : ".mp4";
}

export function useFfmpeg() {
  const [isLoadingCore, setIsLoadingCore] = useState(false);
  const [isTrimming, setIsTrimming] = useState(false);
  const [progress, setProgress] = useState(0);

  const trimVideo = useCallback(
    async (file: File, startSeconds: number, endSeconds: number): Promise<Blob> => {
      setProgress(0);
      const alreadyLoaded = ffmpegSingleton !== null;
      if (!alreadyLoaded) setIsLoadingCore(true);

      const ffmpeg = await getFFmpeg();
      setIsLoadingCore(false);
      setIsTrimming(true);

      const onProgress = ({ progress: value }: { progress: number }) => {
        setProgress(Math.min(1, Math.max(0, value)));
      };
      ffmpeg.on("progress", onProgress);

      const inputName = `input${extensionFromFile(file)}`;
      const outputName = "output.mp4";

      try {
        await ffmpeg.writeFile(inputName, await fetchFile(file));
        await ffmpeg.exec([
          "-ss",
          startSeconds.toFixed(2),
          "-to",
          endSeconds.toFixed(2),
          "-i",
          inputName,
          "-c",
          "copy",
          outputName,
        ]);
        const data = await ffmpeg.readFile(outputName);
        // `data` pode vir com o buffer tipado como ArrayBufferLike
        // (inclui SharedArrayBuffer), que o construtor de Blob rejeita
        // em TS estrito -- copiar para um Uint8Array "normal" resolve
        // sem custo perceptível (arquivo já está inteiro em memória).
        return new Blob([new Uint8Array(data as Uint8Array)], { type: "video/mp4" });
      } finally {
        ffmpeg.off("progress", onProgress);
        try {
          await ffmpeg.deleteFile(inputName);
          await ffmpeg.deleteFile(outputName);
        } catch {
          // arquivo pode nao existir se o exec falhou antes de criar o output -- inofensivo.
        }
        setIsTrimming(false);
      }
    },
    [],
  );

  return { trimVideo, isLoadingCore, isTrimming, progress };
}
