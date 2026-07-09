"""Model AuditLog -- trilha de auditoria administrativa do XHub.

Este model e intencionalmente append-only: nunca deve ser alterado nem
apagado apos criado (ver `AuditLogRepository`, que bloqueia update/delete).
Por isso ele NAO usa `TimestampMixin` (que traz `updated_at` com
`onupdate`) -- so existe `created_at`, fixado no momento da insercao.

Desacoplado de propósito: nao referencia Post/Subscription/etc via
relationship, apenas guarda `target_type` (texto livre, ex.: "user",
"subscription", "twitter_account") e `target_id` (uuid do registro
afetado). Isso permite que qualquer service futuro registre auditoria
sem exigir mudanca neste model.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import AuditAction

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Quem executou a acao. Nullable porque acoes futuras (ex.: um
    # scheduler expirando assinaturas automaticamente) podem nao ter um
    # usuario admin por tras. ondelete=SET NULL preserva o registro
    # historico mesmo que o usuario seja removido.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    action: Mapped[AuditAction] = mapped_column(
        SqlEnum(AuditAction, name="audit_action", native_enum=True),
        nullable=False,
        index=True,
    )

    # Identificacao livre do recurso afetado (sem FK/relationship de
    # proposito, para nao acoplar a auditoria a cada model de dominio).
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    actor: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action.value}>"
