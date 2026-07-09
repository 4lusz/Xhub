"""Repository para o model ScheduledPost."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduled_post import ScheduledPost
from app.repositories.base import BaseRepository


class ScheduledPostRepository(BaseRepository[ScheduledPost]):
    """Acesso a dados dos agendamentos de publicacao."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, ScheduledPost)

    def get_by_post(self, post_id: uuid.UUID) -> ScheduledPost | None:
        statement = select(ScheduledPost).where(ScheduledPost.post_id == post_id)
        return self.db.scalars(statement).first()

    def list_by_executed(
        self, executed: bool, *, offset: int = 0, limit: int = 100
    ) -> Sequence[ScheduledPost]:
        statement = (
            select(ScheduledPost)
            .where(ScheduledPost.executed.is_(executed))
            .order_by(ScheduledPost.scheduled_for.asc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_due(
        self, due_at: datetime, *, offset: int = 0, limit: int = 100
    ) -> Sequence[ScheduledPost]:
        statement = (
            select(ScheduledPost)
            .where(
                ScheduledPost.executed.is_(False),
                ScheduledPost.scheduled_for <= due_at,
            )
            .order_by(ScheduledPost.scheduled_for.asc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_due_for_update_skip_locked(
        self, due_at: datetime, *, limit: int = 25
    ) -> Sequence[ScheduledPost]:
        """Mesma semantica de `list_due`, mas travando as linhas
        retornadas (`SELECT ... FOR UPDATE SKIP LOCKED`).

        Usado exclusivamente pelo worker de agendamento (ver
        `app.scheduler`). `SKIP LOCKED` e o que torna seguro rodar mais
        de um processo/worker do backend simultaneamente (ex.:
        `--workers 2` no Uvicorn, ou multiplas replicas do container):
        cada processo so consegue "ver" e reivindicar agendamentos que
        nenhum outro processo esteja processando neste exato momento --
        nao ha risco de dois processos publicarem o mesmo post agendado
        em duplicidade, sem precisar de nenhuma fila/broker externo.
        """
        statement = (
            select(ScheduledPost)
            .where(
                ScheduledPost.executed.is_(False),
                ScheduledPost.scheduled_for <= due_at,
            )
            .order_by(ScheduledPost.scheduled_for.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return self.db.scalars(statement).all()

