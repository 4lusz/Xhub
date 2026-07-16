"""Repository para o model Post."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import PostStatus
from app.models.post import Post
from app.models.post_account import PostAccount
from app.repositories.base import BaseRepository


class PostRepository(BaseRepository[Post]):
    """Acesso a dados dos posts criados pelos usuarios."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, Post)

    def list_all(
        self,
        *,
        status: PostStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Post]:
        """Lista posts de TODOS os usuarios (visao administrativa, sem
        filtro por `user_id`) -- ver `GET /admin/posts`. Carrega tambem
        `Post.user`, alem do detalhamento por conta ja usado nas demais
        consultas, para permitir identificar de quem e cada post na
        auditoria."""
        statement = (
            select(Post)
            .options(
                selectinload(Post.user),
                selectinload(Post.post_accounts).selectinload(
                    PostAccount.twitter_account
                ),
                selectinload(Post.media),
            )
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(Post.status == status)
        return self.db.scalars(statement).all()

    def list_by_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Post]:
        statement = (
            select(Post)
            .where(Post.user_id == user_id)
            .options(
                selectinload(Post.post_accounts).selectinload(
                    PostAccount.twitter_account
                ),
                selectinload(Post.media),
            )
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_by_status(
        self, status: PostStatus, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Post]:
        statement = (
            select(Post)
            .where(Post.status == status)
            .options(
                selectinload(Post.post_accounts).selectinload(
                    PostAccount.twitter_account
                ),
                selectinload(Post.media),
            )
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def count_by_status(self, status: PostStatus) -> int:
        statement = select(func.count()).select_from(Post).where(Post.status == status)
        return self.db.scalar(statement) or 0

    def list_by_user_and_status(
        self,
        user_id: uuid.UUID,
        status: PostStatus,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Post]:
        statement = (
            select(Post)
            .where(Post.user_id == user_id, Post.status == status)
            .options(
                selectinload(Post.post_accounts).selectinload(
                    PostAccount.twitter_account
                ),
                selectinload(Post.media),
            )
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()
