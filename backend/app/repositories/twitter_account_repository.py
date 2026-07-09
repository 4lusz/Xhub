"""Repository para o model TwitterAccount."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.twitter_account import TwitterAccount
from app.repositories.base import BaseRepository


class TwitterAccountRepository(BaseRepository[TwitterAccount]):
    """Acesso a dados de contas do X conectadas ao usuario."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, TwitterAccount)

    def list_by_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[TwitterAccount]:
        statement = (
            select(TwitterAccount)
            .where(TwitterAccount.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def get_by_user_and_twitter_user_id(
        self, user_id: uuid.UUID, twitter_user_id: str
    ) -> TwitterAccount | None:
        statement = select(TwitterAccount).where(
            TwitterAccount.user_id == user_id,
            TwitterAccount.twitter_user_id == twitter_user_id,
        )
        return self.db.scalars(statement).first()

    def get_by_user_and_username(
        self, user_id: uuid.UUID, username: str
    ) -> TwitterAccount | None:
        statement = select(TwitterAccount).where(
            TwitterAccount.user_id == user_id,
            TwitterAccount.username == username,
        )
        return self.db.scalars(statement).first()

    def list_expired_tokens(self, expires_before: datetime) -> Sequence[TwitterAccount]:
        statement = select(TwitterAccount).where(
            TwitterAccount.expires_at <= expires_before
        )
        return self.db.scalars(statement).all()
