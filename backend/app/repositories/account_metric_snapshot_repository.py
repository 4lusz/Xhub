"""Repository para o model AccountMetricSnapshot.

Append-only, mesmo padrao de `AuditLogRepository`: `update`/`delete`/
`delete_by_id` sao sobrescritos para sempre falhar.
"""

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.models.account_metric_snapshot import AccountMetricSnapshot
from app.repositories.base import BaseRepository

_APPEND_ONLY_MESSAGE = (
    "AccountMetricSnapshot e append-only: registros de metrica nao podem "
    "ser alterados nem removidos."
)


class AccountMetricSnapshotRepository(BaseRepository[AccountMetricSnapshot]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AccountMetricSnapshot)

    def update(
        self, instance: AccountMetricSnapshot, data: Mapping[str, Any]
    ) -> AccountMetricSnapshot:
        raise ConflictException(_APPEND_ONLY_MESSAGE)

    def delete(self, instance: AccountMetricSnapshot) -> None:
        raise ConflictException(_APPEND_ONLY_MESSAGE)

    def delete_by_id(self, id: uuid.UUID) -> bool:
        raise ConflictException(_APPEND_ONLY_MESSAGE)

    def get_latest_by_account(
        self, twitter_account_id: uuid.UUID
    ) -> AccountMetricSnapshot | None:
        statement = (
            select(AccountMetricSnapshot)
            .where(AccountMetricSnapshot.twitter_account_id == twitter_account_id)
            .order_by(AccountMetricSnapshot.collected_at.desc())
            .limit(1)
        )
        return self.db.scalars(statement).first()

    def get_closest_before(
        self, twitter_account_id: uuid.UUID, before: datetime
    ) -> AccountMetricSnapshot | None:
        """Snapshot mais recente coletado ATE `before` -- usado para
        comparar o valor atual com o de N dias atras (tendencia de
        seguidores)."""
        statement = (
            select(AccountMetricSnapshot)
            .where(
                AccountMetricSnapshot.twitter_account_id == twitter_account_id,
                AccountMetricSnapshot.collected_at <= before,
            )
            .order_by(AccountMetricSnapshot.collected_at.desc())
            .limit(1)
        )
        return self.db.scalars(statement).first()

    def list_by_account_since(
        self, twitter_account_id: uuid.UUID, since: datetime
    ) -> Sequence[AccountMetricSnapshot]:
        statement = (
            select(AccountMetricSnapshot)
            .where(
                AccountMetricSnapshot.twitter_account_id == twitter_account_id,
                AccountMetricSnapshot.collected_at >= since,
            )
            .order_by(AccountMetricSnapshot.collected_at)
        )
        return self.db.scalars(statement).all()
