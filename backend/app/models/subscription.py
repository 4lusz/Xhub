"""Model Subscription -- vinculo entre um User e um Plan, com vigencia.

Decisao arquitetural (assinatura unica vs. historico):
Subscription e uma tabela de HISTORICO (append-only por design): cada linha
representa um periodo de vigencia. A renovacao manual feita pelo admin
(`SubscriptionService.renew_subscription`) atualiza a linha existente em
vez de criar uma nova -- por isso, no fluxo atual, cada usuario tende a ter
uma unica linha ao longo do tempo. Nada impede, porem, que uma futura etapa
(ex.: Gestao Administrativa) opte por criar uma nova linha a cada renovacao
para preservar historico completo de planos/vigencias.

Para que as duas formas de uso coexistam sem ambiguidade, a unica garantia
que o banco impoe e: no maximo uma assinatura com status=ACTIVE por
usuario (ver indice parcial `uq_subscriptions_one_active_per_user` abaixo
e a migration correspondente). A assinatura "atual" de um usuario e
definida como a mais recente por `created_at` (ver
`SubscriptionRepository.get_latest_by_user`), nao mais pela data de
expiracao mais distante -- isso evita escolher uma linha antiga por engano
quando existir mais de uma no historico.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import SubscriptionStatus

if TYPE_CHECKING:
    from app.models.plan import Plan
    from app.models.user import User


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        # Garante, no nivel de banco, que um usuario nunca tenha duas
        # assinaturas ACTIVE simultaneamente -- independente de quantas
        # linhas historicas existam com outros status.
        Index(
            "uq_subscriptions_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # ACTIVE/EXPIRED/BLOCKED refletem o estado da ASSINATURA (plano e
    # cota), nao o estado do usuario. Ver `User.is_blocked` para o
    # bloqueio de conta, que e um conceito separado (ver comentario la).
    status: Mapped[SubscriptionStatus] = mapped_column(
        SqlEnum(SubscriptionStatus, name="subscription_status", native_enum=True),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    renewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    used_posts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_posts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user_id={self.user_id} plan_id={self.plan_id}>"
