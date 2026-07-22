"""Repository para o model PostMetricSnapshot.

Append-only, mesmo padrao de `AuditLogRepository`/
`AccountMetricSnapshotRepository`.
"""

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.models.post_account import PostAccount
from app.models.post_metric_snapshot import PostMetricSnapshot
from app.repositories.base import BaseRepository

_APPEND_ONLY_MESSAGE = (
    "PostMetricSnapshot e append-only: registros de metrica nao podem "
    "ser alterados nem removidos."
)


class PostMetricSnapshotRepository(BaseRepository[PostMetricSnapshot]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PostMetricSnapshot)

    def update(
        self, instance: PostMetricSnapshot, data: Mapping[str, Any]
    ) -> PostMetricSnapshot:
        raise ConflictException(_APPEND_ONLY_MESSAGE)

    def delete(self, instance: PostMetricSnapshot) -> None:
        raise ConflictException(_APPEND_ONLY_MESSAGE)

    def delete_by_id(self, id: uuid.UUID) -> bool:
        raise ConflictException(_APPEND_ONLY_MESSAGE)

    def list_by_twitter_account_since(
        self, twitter_account_id: uuid.UUID, since: datetime
    ) -> Sequence[PostMetricSnapshot]:
        statement = (
            select(PostMetricSnapshot)
            .where(
                PostMetricSnapshot.twitter_account_id == twitter_account_id,
                PostMetricSnapshot.collected_at >= since,
            )
            .order_by(PostMetricSnapshot.collected_at)
        )
        return self.db.scalars(statement).all()

    def list_with_published_at_since(
        self, twitter_account_id: uuid.UUID, since: datetime
    ) -> Sequence[tuple[PostMetricSnapshot, datetime]]:
        """Mesmas linhas de `list_by_twitter_account_since`, mas
        acompanhadas do `PostAccount.published_at` correspondente --
        usado para ordenar por data de PUBLICACAO do tweet (nao da
        coleta) na deteccao de anomalia (ver `MetricsService`)."""
        statement = (
            select(PostMetricSnapshot, PostAccount.published_at)
            .join(PostAccount, PostMetricSnapshot.post_account_id == PostAccount.id)
            .where(
                PostMetricSnapshot.twitter_account_id == twitter_account_id,
                PostMetricSnapshot.collected_at >= since,
            )
        )
        return [tuple(row) for row in self.db.execute(statement).all()]

    def list_by_post_account(
        self, post_account_id: uuid.UUID
    ) -> Sequence[PostMetricSnapshot]:
        statement = (
            select(PostMetricSnapshot)
            .where(PostMetricSnapshot.post_account_id == post_account_id)
            .order_by(PostMetricSnapshot.collected_at)
        )
        return self.db.scalars(statement).all()

    def get_latest_by_post_account(
        self, post_account_id: uuid.UUID
    ) -> PostMetricSnapshot | None:
        statement = (
            select(PostMetricSnapshot)
            .where(PostMetricSnapshot.post_account_id == post_account_id)
            .order_by(PostMetricSnapshot.collected_at.desc())
            .limit(1)
        )
        return self.db.scalars(statement).first()
