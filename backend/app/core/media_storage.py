"""Armazenamento em disco dos arquivos de midia de posts.

Segue o mesmo principio de `app.core.crypto`: um helper de baixo nivel,
sem regra de negocio, usado por `MediaService` (upload/validacao) e por
`PostService.delete_post` (limpeza de arquivos ao apagar um post).

Os arquivos ficam em `settings.MEDIA_STORAGE_DIR` (por padrao um
diretorio relativo dentro do bind mount `./backend:/app` do container
backend -- ver docker-compose.yml -- portanto sobrevive a
restarts/recreates do container sem exigir um volume Docker adicional),
organizados por usuario (`{MEDIA_STORAGE_DIR}/{user_id}/{uuid}{ext}`)
para manter o diretorio previsivel e evitar colisao de nomes.

`PostMedia.storage_path` grava sempre o caminho RELATIVO retornado por
`save_upload`/gerado aqui -- nunca um caminho absoluto do host -- para
que o valor persistido no banco continue valido mesmo se
`MEDIA_STORAGE_DIR` mudar de local entre ambientes.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import BinaryIO

from app.config.settings import settings
from app.core.exceptions import ValidationException


class MediaTooLargeError(ValidationException):
    default_message = "Arquivo de midia excede o tamanho maximo permitido."
    default_code = "media_too_large"


def _storage_root() -> Path:
    root = Path(settings.MEDIA_STORAGE_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_path(storage_path: str) -> Path:
    """Resolve um `storage_path` relativo (persistido no banco) para um
    caminho absoluto no filesystem do container."""
    return _storage_root() / storage_path


def save_upload(
    *,
    user_id: uuid.UUID,
    file_obj: BinaryIO,
    extension: str,
    max_size_bytes: int,
    chunk_size: int = 1024 * 1024,
) -> tuple[str, int]:
    """Grava `file_obj` em disco em streaming (nunca carrega o arquivo
    inteiro em memoria), interrompendo e limpando o arquivo parcial se
    `max_size_bytes` for excedido. Retorna `(storage_path_relativo,
    tamanho_em_bytes)`.
    """
    user_dir = _storage_root() / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}{extension}"
    relative_path = f"{user_id}/{filename}"
    absolute_path = user_dir / filename

    total_bytes = 0
    try:
        with absolute_path.open("wb") as destination:
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > max_size_bytes:
                    raise MediaTooLargeError(
                        "Arquivo excede o tamanho maximo permitido para "
                        "este tipo de midia."
                    )

                destination.write(chunk)
    except Exception:
        absolute_path.unlink(missing_ok=True)
        raise

    return relative_path, total_bytes


def delete_file(storage_path: str) -> None:
    """Remove o arquivo do disco, sem erro se ele ja nao existir (idempotente)."""
    resolve_path(storage_path).unlink(missing_ok=True)
