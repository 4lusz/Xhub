"""Regras puras de midia (imagem/gif/video) anexada a um Post.

Segue o mesmo padrao de `app.domain.content_invariants` e
`app.domain.policies`: funcoes puras, sem I/O, sem SQLAlchemy, sem
FastAPI. Usado por `MediaService` (validacao no upload de um arquivo
individual) e `PostService` (validacao da combinacao de midias
anexadas a um post antes de criar/publicar).

Limites e categorias seguem a API oficial de upload de midia do X
(`POST https://api.x.com/2/media/upload`):
- Imagem (JPEG/PNG/WEBP): ate 5MB, ate 4 por post.
- GIF (estatico ou animado -- nao diferenciamos sem uma lib de imagem
  dedicada, ver nota abaixo): ate 15MB, exatamente 1 por post (nao pode
  ser combinado com outra midia).
- Video (MP4): ate 512MB, exatamente 1 por post (nao pode ser
  combinado com outra midia).

Nota tecnica: distinguir GIF animado de GIF estatico exigiria decodificar
o arquivo (ex.: Pillow), dependencia nao adicionada nesta etapa por nao
ser estritamente necessaria -- todo upload com `content_type=image/gif`
e tratado como categoria "gif" (mais restritiva), o que e sempre seguro
do ponto de vista da API do X mesmo para um GIF estatico.
"""

from __future__ import annotations

from dataclasses import dataclass

MediaTypeName = str  # "image" | "gif" | "video" -- ver app.models.enums.MediaType

MAX_MEDIA_PER_POST = 4

_BYTES_PER_MB = 1024 * 1024

MEDIA_TYPE_IMAGE = "image"
MEDIA_TYPE_GIF = "gif"
MEDIA_TYPE_VIDEO = "video"

# Content-Type (MIME) aceito -> categoria de midia. Lista de permissao
# explicita -- qualquer content_type fora daqui e rejeitado no upload.
ALLOWED_CONTENT_TYPES: dict[str, MediaTypeName] = {
    "image/jpeg": MEDIA_TYPE_IMAGE,
    "image/png": MEDIA_TYPE_IMAGE,
    "image/webp": MEDIA_TYPE_IMAGE,
    "image/gif": MEDIA_TYPE_GIF,
    "video/mp4": MEDIA_TYPE_VIDEO,
}

# Extensao de arquivo usada ao gravar em disco, por content_type.
_FILE_EXTENSIONS: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
}

MAX_SIZE_BYTES_BY_MEDIA_TYPE: dict[MediaTypeName, int] = {
    MEDIA_TYPE_IMAGE: 5 * _BYTES_PER_MB,
    MEDIA_TYPE_GIF: 15 * _BYTES_PER_MB,
    MEDIA_TYPE_VIDEO: 512 * _BYTES_PER_MB,
}

# Categoria exigida pelo `media_category` do endpoint INIT de upload do
# X para cada tipo -- afeta limites e processamento (assincrono para
# gif/video) do lado do X.
X_MEDIA_CATEGORY_BY_MEDIA_TYPE: dict[MediaTypeName, str] = {
    MEDIA_TYPE_IMAGE: "tweet_image",
    MEDIA_TYPE_GIF: "tweet_gif",
    MEDIA_TYPE_VIDEO: "tweet_video",
}


@dataclass(frozen=True)
class MediaValidationError:
    message: str


def classify_content_type(content_type: str) -> MediaTypeName | None:
    """Retorna a categoria de midia para um `content_type`, ou `None`
    se nao for um tipo suportado."""
    return ALLOWED_CONTENT_TYPES.get(content_type.lower().strip())


def file_extension_for_content_type(content_type: str) -> str:
    return _FILE_EXTENSIONS.get(content_type.lower().strip(), "")


def max_size_bytes_for(media_type: MediaTypeName) -> int:
    return MAX_SIZE_BYTES_BY_MEDIA_TYPE[media_type]


def x_media_category_for(media_type: MediaTypeName) -> str:
    return X_MEDIA_CATEGORY_BY_MEDIA_TYPE[media_type]


def validate_media_combination(media_types: list[MediaTypeName]) -> str | None:
    """Valida a combinacao de midias anexadas a um UNICO post, seguindo
    as regras oficiais do X. Retorna uma mensagem de erro em portugues
    quando invalida, ou `None` quando valida.

    Regras:
    - No maximo `MAX_MEDIA_PER_POST` itens.
    - Video: nao pode ser combinado com nenhuma outra midia (apenas 1
      video sozinho).
    - GIF: nao pode ser combinado com nenhuma outra midia (apenas 1 gif
      sozinho).
    - Imagens: ate `MAX_MEDIA_PER_POST` imagens, sem gif/video juntos.
    """
    if not media_types:
        return None

    if len(media_types) > MAX_MEDIA_PER_POST:
        return f"Um post pode ter no maximo {MAX_MEDIA_PER_POST} arquivos de midia."

    has_video = MEDIA_TYPE_VIDEO in media_types
    has_gif = MEDIA_TYPE_GIF in media_types

    if has_video and len(media_types) > 1:
        return "Um video nao pode ser combinado com outras imagens/gifs no mesmo post."

    if has_gif and len(media_types) > 1:
        return "Um GIF nao pode ser combinado com outras imagens/videos no mesmo post."

    return None
