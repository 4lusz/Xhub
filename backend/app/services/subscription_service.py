"""Service de assinaturas."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.domain.contexts import PlanLimits, PlanUsage, SubscriptionContext
from app.domain.enums import SubscriptionStatus as DomainSubscriptionStatus
from app.domain.policies import (
    ensure_subscription_active,
    ensure_sufficient_posts,
    get_available_posts,
)
from app.models.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService, NotFoundError, ValidationError


class SubscriptionService(BaseService[Subscription]):
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        user_repository: UserRepository,
        plan_repository: PlanRepository,
    ) -> None:
        super().__init__(subscription_repository)
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository
        self.plan_repository = plan_repository

    def list_user_subscriptions(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[Subscription]:
        self._ensure_user_exists(user_id)
        return self.subscription_repository.list_by_user(
            user_id, offset=offset, limit=limit
        )

    def get_current_subscription(self, user_id: uuid.UUID) -> Subscription | None:
        self._ensure_user_exists(user_id)
        return self.subscription_repository.get_latest_by_user(user_id)

    def get_current_subscription_for_update(
        self, user_id: uuid.UUID
    ) -> Subscription | None:
        """Mesma semantica de `get_current_subscription`, mas com o
        registro travado (`SELECT ... FOR UPDATE`) ate o fim da
        transacao -- usar apenas quando a assinatura sera validada e,
        na sequencia, ter seu saldo consumido dentro da mesma
        transacao (ex.: publicacao de post)."""
        self._ensure_user_exists(user_id)
        return self.subscription_repository.get_latest_by_user_for_update(user_id)

    def ensure_can_publish(
        self, user_id: uuid.UUID, *, required_posts: int
    ) -> Subscription:
        """Valida, de forma atomica e ANTES de qualquer efeito colateral
        externo, que o usuario tem assinatura ativa e saldo suficiente
        para publicar `required_posts` posts. Retorna a assinatura (ja
        travada) para uso no restante da transacao.

        Levanta excecao e nao permite nenhuma publicacao caso a
        assinatura nao exista, esteja inativa/bloqueada/expirada ou nao
        tenha saldo suficiente.
        """
        subscription = self.get_current_subscription_for_update(user_id)

        if subscription is None:
            raise ValidationError("Usuario nao possui assinatura ativa.")

        context = self.to_domain_context(subscription)
        ensure_subscription_active(context)
        ensure_sufficient_posts(context, required_posts=required_posts)

        return subscription

    def create_subscription(
        self, *, user_id: uuid.UUID, plan_id: uuid.UUID, expires_at: datetime
    ) -> Subscription:
        self._ensure_user_exists(user_id)
        self._ensure_plan_exists(plan_id)
        return self.subscription_repository.create(
            {
                "user_id": user_id,
                "plan_id": plan_id,
                "expires_at": expires_at,
                "status": SubscriptionStatus.ACTIVE,
                "used_posts": 0,
                "extra_posts": 0,
            }
        )

    def renew_subscription(
        self,
        subscription_id: uuid.UUID,
        *,
        expires_at: datetime,
        plan_id: uuid.UUID | None = None,
    ) -> Subscription:
        subscription = self.ensure_exists(
            subscription_id,
            message="Assinatura nao encontrada.",
        )
        data: dict[str, object] = {
            "expires_at": expires_at,
            "renewed_at": datetime.now(UTC),
            "status": SubscriptionStatus.ACTIVE,
            "used_posts": 0,
        }
        if plan_id is not None:
            self._ensure_plan_exists(plan_id)
            data["plan_id"] = plan_id

        return self.subscription_repository.update(subscription, data)

    def block_subscription(self, subscription_id: uuid.UUID) -> Subscription:
        subscription = self.ensure_exists(
            subscription_id,
            message="Assinatura nao encontrada.",
        )
        return self.subscription_repository.update(
            subscription,
            {"status": SubscriptionStatus.BLOCKED},
        )

    def expire_subscription(self, subscription_id: uuid.UUID) -> Subscription:
        subscription = self.ensure_exists(
            subscription_id,
            message="Assinatura nao encontrada.",
        )
        return self.subscription_repository.update(
            subscription,
            {"status": SubscriptionStatus.EXPIRED},
        )

    def add_extra_posts(self, subscription_id: uuid.UUID, amount: int) -> Subscription:
        if amount <= 0:
            raise ValidationError("Quantidade de posts extras deve ser positiva.")

        subscription = self.ensure_exists(
            subscription_id,
            message="Assinatura nao encontrada.",
        )
        return self.subscription_repository.update(
            subscription,
            {"extra_posts": subscription.extra_posts + amount},
        )

    def remove_extra_posts(self, subscription_id: uuid.UUID, amount: int) -> Subscription:
        if amount <= 0:
            raise ValidationError("Quantidade de posts extras deve ser positiva.")

        subscription = self.ensure_exists(
            subscription_id,
            message="Assinatura nao encontrada.",
        )
        if amount > subscription.extra_posts:
            raise ValidationError("Quantidade maior que os posts extras disponiveis.")

        return self.subscription_repository.update(
            subscription,
            {"extra_posts": subscription.extra_posts - amount},
        )

    def consume_posts(self, subscription_id: uuid.UUID, amount: int) -> Subscription:
        subscription = self.subscription_repository.get_for_update(subscription_id)
        if subscription is None:
            raise NotFoundError("Assinatura nao encontrada.")
        context = self.to_domain_context(subscription)
        ensure_subscription_active(context)
        ensure_sufficient_posts(
            context,
            required_posts=amount,
        )
        return self.subscription_repository.update(
            subscription,
            {"used_posts": subscription.used_posts + amount},
        )

    def get_available_posts(self, subscription: Subscription) -> int:
        return get_available_posts(self.to_domain_context(subscription))

    def ensure_can_connect_account(
        self,
        user_id: uuid.UUID,
        *,
        for_update: bool = True,
    ) -> None:
        subscription = (
            self.get_current_subscription_for_update(user_id)
            if for_update
            else self.get_current_subscription(user_id)
        )

        if subscription is None:
            raise ValidationError("Usuario nao possui assinatura ativa.")

        context = self.to_domain_context(subscription)

        ensure_subscription_active(context)

        if (
            context.usage.connected_accounts
            >= context.plan_limits.max_accounts
        ):
            raise ValidationError(
                "Limite de contas do plano atingido."
            )
        
    def to_domain_context(self, subscription: Subscription) -> SubscriptionContext:
        return SubscriptionContext(
            status=DomainSubscriptionStatus(subscription.status.value),
            expires_at=subscription.expires_at,
            plan_limits=PlanLimits(
                max_accounts=subscription.plan.max_accounts,
                max_posts_month=subscription.plan.max_posts_month,
            ),
            usage=PlanUsage(
                connected_accounts=len(subscription.user.twitter_accounts),
                used_posts=subscription.used_posts,
                extra_posts=subscription.extra_posts,
            ),
        )

    def _ensure_user_exists(self, user_id: uuid.UUID) -> None:
        if self.user_repository.get(user_id) is None:
            raise NotFoundError("Usuario nao encontrado.")

    def _ensure_plan_exists(self, plan_id: uuid.UUID) -> None:
        if self.plan_repository.get(plan_id) is None:
            raise NotFoundError("Plano nao encontrado.")
