"""Repository para o model AuditLog.

Append-only por regra de negocio: `update`, `delete` e `delete_by_id` sao
sobrescritos para sempre falhar, mesmo que algum service futuro tente
chama-los por engano (o `BaseRepository` generico permite as duas
operacoes, entao aqui elas sao explicitamente bloqueadas).
"""

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.models.audit_log import AuditLog
from app.models.enums import AuditAction
from app.repositories.base import BaseRepository

_APPEND_ONLY_MESSAGE = (
    "AuditLog e append-only: registros de auditoria nao podem ser "
    "alterados nem removidos."
)


class AuditLogRepository(BaseRepository[AuditLog]):
    """Acesso a dados da trilha de auditoria administrativa."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, AuditLog)

    def update(self, instance: AuditLog, data: Mapping[str, Any]) -> AuditLog:
        raise ConflictException(_APPEND_ONLY_MESSAGE)

    def delete(self, instance: AuditLog) -> None:
        raise ConflictException(_APPEND_ONLY_MESSAGE)

    def delete_by_id(self, id: uuid.UUID) -> bool:
        raise ConflictException(_APPEND_ONLY_MESSAGE)

    def list_by_actor(
        self, actor_user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[AuditLog]:
        statement = (
            select(AuditLog)
            .where(AuditLog.actor_user_id == actor_user_id)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_by_target(
        self,
        target_type: str,
        target_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[AuditLog]:
        statement = (
            select(AuditLog)
            .where(
                AuditLog.target_type == target_type,
                AuditLog.target_id == target_id,
            )
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_by_action(
        self, action: AuditAction, *, offset: int = 0, limit: int = 100
    ) -> Sequence[AuditLog]:
        statement = (
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_recent(self, *, offset: int = 0, limit: int = 100) -> Sequence[AuditLog]:
        statement = (
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()
