import uuid
from types import SimpleNamespace

from app.routes import admin


def test_get_subscription_returns_subscription_for_admin(client):
    """Correcao (auditoria funcional): este teste ficava desatualizado em
    relacao a `SubscriptionService`/`SubscriptionResponse` desde a
    funcionalidade que adicionou `available_posts`/`used_accounts`/`plan`
    a resposta (usados pela tela "Assinatura" do admin) e o metodo
    `to_domain_context` ao service real -- o dublê `FakeSubscriptionService`
    nunca foi atualizado para acompanhar, entao `_to_subscription_response`
    (`app.routes.admin`) sempre levantava `AttributeError` ao chamar
    `to_domain_context`/`get_available_posts`, que o dublê nao implementava.
    Atualizado para implementar a mesma interface do service real e para
    validar o corpo de resposta completo e atual."""
    subscription_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    plan_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
    dummy_admin = SimpleNamespace(id=uuid.UUID(int=1))

    plan = SimpleNamespace(
        id=plan_id,
        name="Creator",
        price=99.0,
        max_accounts=5,
        max_posts_month=300,
    )
    subscription = SimpleNamespace(
        id=subscription_id,
        user_id=user_id,
        plan_id=plan_id,
        status="active",
        expires_at="2026-01-01T00:00:00Z",
        renewed_at=None,
        used_posts=10,
        extra_posts=0,
        plan=plan,
    )

    class FakeSubscriptionService:
        def ensure_exists(self, _subscription_id: uuid.UUID, message: str):
            assert _subscription_id == subscription_id
            return subscription

        def to_domain_context(self, _subscription):
            from app.domain.contexts import PlanLimits, PlanUsage, SubscriptionContext
            from app.domain.enums import SubscriptionStatus as DomainSubscriptionStatus

            return SubscriptionContext(
                status=DomainSubscriptionStatus.ACTIVE,
                expires_at=_subscription.expires_at,
                plan_limits=PlanLimits(
                    max_accounts=plan.max_accounts,
                    max_posts_month=plan.max_posts_month,
                ),
                usage=PlanUsage(
                    connected_accounts=2,
                    used_posts=_subscription.used_posts,
                    extra_posts=_subscription.extra_posts,
                ),
            )

        def get_available_posts(self, _subscription):
            return plan.max_posts_month - _subscription.used_posts

    client.app.dependency_overrides[admin.get_current_admin] = lambda: dummy_admin
    client.app.dependency_overrides[admin.get_subscription_service] = (
        lambda: FakeSubscriptionService()
    )

    response = client.get(f"/api/v1/admin/subscriptions/{subscription_id}")
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": str(subscription_id),
        "user_id": str(user_id),
        "plan_id": str(plan_id),
        "status": "active",
        "expires_at": "2026-01-01T00:00:00Z",
        "renewed_at": None,
        "used_posts": 10,
        "extra_posts": 0,
        "available_posts": 290,
        "used_accounts": 2,
        "plan": {
            "id": str(plan_id),
            "name": "Creator",
            "price": 99.0,
            "max_accounts": 5,
            "max_posts_month": 300,
        },
    }


def test_get_user_subscription_returns_404_when_missing(client):
    dummy_admin = SimpleNamespace(id=uuid.UUID(int=1))
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000004")

    class FakeSubscriptionService:
        def get_current_subscription(self, _user_id: uuid.UUID):
            assert _user_id == user_id
            return None

    client.app.dependency_overrides[admin.get_current_admin] = lambda: dummy_admin
    client.app.dependency_overrides[admin.get_subscription_service] = (
        lambda: FakeSubscriptionService()
    )

    response = client.get(f"/api/v1/admin/users/{user_id}/subscription")
    client.app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Assinatura nao encontrada para esse usuario."
