/**
 * Copia os artefatos do @ffmpeg/core (ffmpeg-core.js/.wasm) para
 * public/ffmpeg/ apos o npm install, para que sejam servidos como
 * assets estaticos do MESMO origin do frontend (sem depender de CDN
 * de terceiros para o corte de video no navegador -- ver
 * hooks/useFfmpeg.ts). Nao versionado no git (32MB) -- regenerado
 * automaticamente a cada `npm install` (postinstall), no mesmo
 * espirito do "npm install a cada start" ja usado no docker-compose.
 */
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const src = join(root, "node_modules/@ffmpeg/core/dist/umd");
const dest = join(root, "public/ffmpeg");

if (!existsSync(src)) {
  console.warn("[copy-ffmpeg-core] @ffmpeg/core nao encontrado em node_modules -- pulando.");
  process.exit(0);
}

mkdirSync(dest, { recursive: true });

for (const file of ["ffmpeg-core.js", "ffmpeg-core.wasm"]) {
  copyFileSync(join(src, file), join(dest, file));
}

console.log("[copy-ffmpeg-core] ffmpeg-core copiado para public/ffmpeg/.");
