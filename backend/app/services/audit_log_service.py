"""Service de auditoria administrativa.

Desacoplado de proposito: nao depende de nenhum outro service de dominio
(User, Subscription, etc.), apenas do proprio repository. Isso permite que
qualquer service ou rota futura injete `AuditLogService` e registre uma
acao sem criar dependencia circular.

Assim como o restante da camada de service, `record()` nao da commit --
quem chama (rota ou outro service, dentro da mesma transacao) decide
quando commitar.
"""

import uuid
from collections.abc import Sequence

from app.models.audit_log import AuditLog
from app.models.enums import AuditAction
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.base_service import BaseService


class AuditLogService(BaseService[AuditLog]):
    def __init__(self, audit_log_repository: AuditLogRepository) -> None:
        super().__init__(audit_log_repository)
        self.audit_log_repository = audit_log_repository

    def record(
        self,
        *,
        action: AuditAction,
        actor_user_id: uuid.UUID | None = None,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        description: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        """Registra uma entrada de auditoria (append-only)."""
        return self.audit_log_repository.create(
            {
                "action": action,
                "actor_user_id": actor_user_id,
                "target_type": target_type,
                "target_id": target_id,
                "description": description,
                "details": details,
            }
        )

    def list_by_actor(
        self, actor_user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[AuditLog]:
        return self.audit_log_repository.list_by_actor(
            actor_user_id, offset=offset, limit=limit
        )

    def list_by_target(
        self,
        target_type: str,
        target_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[AuditLog]:
        return self.audit_log_repository.list_by_target(
            target_type, target_id, offset=offset, limit=limit
        )

    def list_by_action(
        self, action: AuditAction, *, offset: int = 0, limit: int = 100
    ) -> Sequence[AuditLog]:
        return self.audit_log_repository.list_by_action(
            action, offset=offset, limit=limit
        )

    def list_recent(self, *, offset: int = 0, limit: int = 100) -> Sequence[AuditLog]:
        return self.audit_log_repository.list_recent(offset=offset, limit=limit)
