"""Repository para o model Post."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import PostStatus
from app.models.post import Post
from app.repositories.base import BaseRepository


class PostRepository(BaseRepository[Post]):
    """Acesso a dados dos posts criados pelos usuarios."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, Post)

    def list_by_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Post]:
        statement = (
            select(Post)
            .where(Post.user_id == user_id)
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
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

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
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()
