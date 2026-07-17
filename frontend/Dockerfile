FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
# --ignore-scripts: nesta camada so package.json/package-lock.json
# foram copiados (para aproveitar o cache de camada do Docker) --
# scripts/copy-ffmpeg-core.mjs (postinstall) ainda nao existe aqui, so
# apos o COPY . . abaixo. O install real (com postinstall completo) ja
# roda de qualquer forma a cada start do container, via `command:` no
# docker-compose.yml (bind mount com o codigo-fonte completo) -- este
# aqui e so para aquecer a camada de imagem.
RUN npm install --ignore-scripts

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
