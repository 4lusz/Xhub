"""Service de midia (imagem/gif/video) anexada a posts.

Ver docs/ROADMAP_MEDIA.md. Responsabilidades:

- Validar e armazenar em disco um arquivo enviado pelo usuario
  (`upload_media`), ANTES de qualquer post existir -- mesmo fluxo do
  compositor do X (upload com preview imediato).
- Autorizar o download/preview de uma midia (dono do arquivo apenas).
- Remover uma midia ainda nao anexada a nenhum post.

Nunca fala com a API do X -- isso e responsabilidade de `XOAuthClient`
(chamado a partir de `PostService.publish_post` no momento da
publicacao, ver app/oauth/oauth_client.py).
"""

from __future__ import annotations

import uuid

from fastapi import UploadFile

from app.core import media_storage
from app.domain.media_rules import classify_content_type, file_extension_for_content_type, max_size_bytes_for
from app.models.enums import MediaType
from app.models.post_media import PostMedia
from app.repositories.post_media_repository import PostMediaRepository
from app.services.base_service import BaseService, NotFoundError, ValidationError


class MediaService(BaseService[PostMedia]):
    def __init__(self, post_media_repository: PostMediaRepository) -> None:
        super().__init__(post_media_repository)
        self.post_media_repository = post_media_repository

    def upload_media(self, *, user_id: uuid.UUID, upload_file: UploadFile) -> PostMedia:
        content_type = (upload_file.content_type or "").lower().strip()
        media_type_name = classify_content_type(content_type)

        if media_type_name is None:
            raise ValidationError(
                "Tipo de arquivo nao suportado. Envie uma imagem "
                "(JPEG, PNG ou WEBP), um GIF ou um video MP4."
            )

        max_size_bytes = max_size_bytes_for(media_type_name)
        extension = file_extension_for_content_type(content_type)

        storage_path, file_size_bytes = media_storage.save_upload(
            user_id=user_id,
            file_obj=upload_file.file,
            extension=extension,
            max_size_bytes=max_size_bytes,
        )

        return self.post_media_repository.create(
            {
                "post_id": None,
                "user_id": user_id,
                "media_type": MediaType(media_type_name),
                "storage_path": storage_path,
                "content_type": content_type,
                "file_size_bytes": file_size_bytes,
                "position": None,
            }
        )

    def get_owned_media(self, media_id: uuid.UUID, user_id: uuid.UUID) -> PostMedia:
        media = self.post_media_repository.get(media_id)
        if media is None or media.user_id != user_id:
            raise NotFoundError("Midia nao encontrada.")
        return media

    def delete_unattached_media(self, media_id: uuid.UUID, user_id: uuid.UUID) -> None:
        media = self.get_owned_media(media_id, user_id)

        if media.post_id is not None:
            raise ValidationError(
                "Esta midia ja foi anexada a um post e nao pode mais ser removida isoladamente."
            )

        media_storage.delete_file(media.storage_path)
        self.post_media_repository.delete(media)
