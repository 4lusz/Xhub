"""Repository para o model PostMedia."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.post_media import PostMedia
from app.repositories.base import BaseRepository


class PostMediaRepository(BaseRepository[PostMedia]):
    """Acesso a dados de midia (imagem/gif/video) anexada a posts."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, PostMedia)

    def list_by_post(self, post_id: uuid.UUID) -> Sequence[PostMedia]:
        statement = (
            select(PostMedia)
            .where(PostMedia.post_id == post_id)
            .order_by(PostMedia.position)
        )
        return self.db.scalars(statement).all()

    def list_by_ids_and_user(
        self, media_ids: Sequence[uuid.UUID], user_id: uuid.UUID
    ) -> Sequence[PostMedia]:
        """Busca midias pertencentes ao usuario e AINDA NAO anexadas a
        nenhum post (`post_id IS NULL`) -- usado para validar
        `media_ids` recebido em `POST /posts` antes de anexa-los."""
        statement = select(PostMedia).where(
            PostMedia.id.in_(media_ids),
            PostMedia.user_id == user_id,
            PostMedia.post_id.is_(None),
        )
        return self.db.scalars(statement).all()

    def attach_to_post(
        self, media: PostMedia, *, post_id: uuid.UUID, position: int
    ) -> PostMedia:
        return self.update(media, {"post_id": post_id, "position": position})
