"""Repository para o model PostAccount."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import PostAccountStatus
from app.models.post_account import PostAccount
from app.repositories.base import BaseRepository


class PostAccountRepository(BaseRepository[PostAccount]):
    """Acesso a dados do fan-out de publicacao por conta do X."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, PostAccount)

    def list_by_post(self, post_id: uuid.UUID) -> Sequence[PostAccount]:
        statement = select(PostAccount).where(PostAccount.post_id == post_id)
        return self.db.scalars(statement).all()

    def list_pending_or_failed_by_post_for_update_skip_locked(
        self, post_id: uuid.UUID
    ) -> Sequence[PostAccount]:
        statement = (
            select(PostAccount)
            .where(
                PostAccount.post_id == post_id,
                PostAccount.status != PostAccountStatus.PUBLISHED,
            )
            .with_for_update(skip_locked=True)
        )
        return self.db.scalars(statement).all()

    def list_by_twitter_account(
        self,
        twitter_account_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[PostAccount]:
        statement = (
            select(PostAccount)
            .where(PostAccount.twitter_account_id == twitter_account_id)
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_by_status(
        self, status: PostAccountStatus, *, offset: int = 0, limit: int = 100
    ) -> Sequence[PostAccount]:
        statement = (
            select(PostAccount)
            .where(PostAccount.status == status)
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def get_by_post_and_twitter_account(
        self, post_id: uuid.UUID, twitter_account_id: uuid.UUID
    ) -> PostAccount | None:
        statement = select(PostAccount).where(
            PostAccount.post_id == post_id,
            PostAccount.twitter_account_id == twitter_account_id,
        )
        return self.db.scalars(statement).first()
