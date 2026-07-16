/**
 * Gera, via canvas, a imagem final recortada/girada a partir de uma
 * imagem de origem e uma area de recorte (em pixels da imagem
 * original) -- mesmo padrao de referencia do `react-easy-crop`
 * (biblioteca usada em `components/posts/ImageEditorDialog.tsx`).
 * Roda inteiramente no navegador; o resultado (Blob) e o que
 * efetivamente vira o arquivo enviado a `POST /media/upload`.
 *
 * So se aplica a imagens estaticas (JPEG/PNG/WEBP) -- um GIF animado
 * perderia a animacao se passasse por aqui (canvas so captura um
 * frame), por isso a edicao de midia nunca oferece este editor para
 * `media_type === "gif"` (ver `components/posts/MediaComposer.tsx`).
 */

export interface PixelCropArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => resolve(image));
    image.addEventListener("error", () => reject(new Error("Falha ao carregar a imagem.")));
    image.src = url;
  });
}

function toRadians(degrees: number): number {
  return (degrees * Math.PI) / 180;
}

function rotatedBoundingBox(width: number, height: number, rotationDegrees: number) {
  const radians = toRadians(rotationDegrees);
  return {
    width: Math.abs(Math.cos(radians) * width) + Math.abs(Math.sin(radians) * height),
    height: Math.abs(Math.sin(radians) * width) + Math.abs(Math.cos(radians) * height),
  };
}

export async function getCroppedImageBlob(
  imageSrc: string,
  pixelCrop: PixelCropArea,
  rotationDegrees = 0,
  mimeType = "image/jpeg",
  quality = 0.92,
): Promise<Blob> {
  const image = await loadImage(imageSrc);

  const { width: boxWidth, height: boxHeight } = rotatedBoundingBox(
    image.width,
    image.height,
    rotationDegrees,
  );

  const rotationCanvas = document.createElement("canvas");
  rotationCanvas.width = boxWidth;
  rotationCanvas.height = boxHeight;
  const rotationCtx = rotationCanvas.getContext("2d");
  if (!rotationCtx) throw new Error("Canvas 2D indisponível neste navegador.");

  rotationCtx.translate(boxWidth / 2, boxHeight / 2);
  rotationCtx.rotate(toRadians(rotationDegrees));
  rotationCtx.translate(-image.width / 2, -image.height / 2);
  rotationCtx.drawImage(image, 0, 0);

  const outputCanvas = document.createElement("canvas");
  outputCanvas.width = pixelCrop.width;
  outputCanvas.height = pixelCrop.height;
  const outputCtx = outputCanvas.getContext("2d");
  if (!outputCtx) throw new Error("Canvas 2D indisponível neste navegador.");

  outputCtx.drawImage(
    rotationCanvas,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    pixelCrop.width,
    pixelCrop.height,
  );

  return new Promise((resolve, reject) => {
    outputCanvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Falha ao gerar a imagem recortada."))),
      mimeType,
      quality,
    );
  });
}
