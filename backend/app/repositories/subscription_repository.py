"""Repository para o model Subscription."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    """Acesso a dados de assinaturas de usuarios."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, Subscription)

    def list_by_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Subscription]:
        statement = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.expires_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_by_plan(
        self, plan_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Subscription]:
        statement = (
            select(Subscription)
            .where(Subscription.plan_id == plan_id)
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def get_latest_by_user_for_update(self, user_id: uuid.UUID) -> Subscription | None:
        """Igual a `get_latest_by_user`, mas com `SELECT ... FOR UPDATE`.

        Usado nos pontos que fazem checagem-e-consumo de creditos/limites
        (ex.: `PostService.publish_post`) para fechar a janela de corrida
        entre "ler saldo disponivel" e "gravar saldo consumido" quando
        duas requisicoes concorrentes operam sobre a mesma assinatura.
        A trava e liberada automaticamente no commit/rollback da
        transacao da requisicao.
        """
        statement = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
            .with_for_update()
        )
        return self.db.scalars(statement).first()

    def get_for_update(self, subscription_id: uuid.UUID) -> Subscription | None:
        statement = (
            select(Subscription)
            .where(Subscription.id == subscription_id)
            .with_for_update()
        )
        return self.db.scalars(statement).first()

    def get_latest_by_user(self, user_id: uuid.UUID) -> Subscription | None:
        """Retorna a assinatura "atual" do usuario.

        Definida como a mais recente por `created_at`, e nao pela data de
        expiracao mais distante: como Subscription pode acumular historico
        (ver docstring do model), ordenar por `expires_at` poderia
        selecionar uma linha antiga caso ela tivesse, por qualquer motivo,
        uma vigencia futura maior que a da assinatura realmente vigente.
        """
        statement = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(statement).first()

    def get_latest_by_user_and_status(
        self, user_id: uuid.UUID, status: SubscriptionStatus
    ) -> Subscription | None:
        statement = (
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.status == status)
            .order_by(Subscription.expires_at.desc())
            .limit(1)
        )
        return self.db.scalars(statement).first()

    def list_by_status(
        self, status: SubscriptionStatus, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Subscription]:
        statement = (
            select(Subscription)
            .where(Subscription.status == status)
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_expiring_before(self, expires_before: datetime) -> Sequence[Subscription]:
        statement = select(Subscription).where(
            Subscription.expires_at <= expires_before
        )
        return self.db.scalars(statement).all()
