"""Repository para o model PostMedia."""

import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select
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

    def list_for_post_account(
        self, *, post_id: uuid.UUID, post_account_id: uuid.UUID
    ) -> Sequence[PostMedia]:
        """Midia que se aplica a UMA conta especifica de um post: a
        compartilhada entre todas (`post_account_id IS NULL`) mais a
        exclusiva dessa conta, se houver (ver
        `app.models.enums.PostCompositionMode`). Usado por
        `PostService.publish_post` para saber o que enviar ao X para
        cada conta."""
        statement = (
            select(PostMedia)
            .where(
                PostMedia.post_id == post_id,
                or_(
                    PostMedia.post_account_id.is_(None),
                    PostMedia.post_account_id == post_account_id,
                ),
            )
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
        self,
        media: PostMedia,
        *,
        post_id: uuid.UUID,
        position: int,
        post_account_id: uuid.UUID | None = None,
    ) -> PostMedia:
        return self.update(
            media,
            {
                "post_id": post_id,
                "position": position,
                "post_account_id": post_account_id,
            },
        )
