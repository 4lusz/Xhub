import uuid
from types import SimpleNamespace

from app.routes import admin


def test_get_subscription_returns_subscription_for_admin(client):
    subscription_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    plan_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
    dummy_admin = SimpleNamespace(id=uuid.UUID(int=1))

    class FakeSubscriptionService:
        def ensure_exists(self, _subscription_id: uuid.UUID, message: str):
            assert _subscription_id == subscription_id
            return SimpleNamespace(
                id=subscription_id,
                user_id=user_id,
                plan_id=plan_id,
                status="active",
                expires_at="2026-01-01T00:00:00Z",
                renewed_at=None,
                used_posts=0,
                extra_posts=0,
            )

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
        "used_posts": 0,
        "extra_posts": 0,
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
