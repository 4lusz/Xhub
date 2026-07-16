import uuid
from types import SimpleNamespace

from app.routes import oauth


def test_oauth_login_returns_authorization_url(client):
    dummy_user = SimpleNamespace(id=uuid.UUID(int=1))

    class FakeOAuthService:
        def build_login_url(self, user_id: uuid.UUID) -> str:
            assert user_id == dummy_user.id
            return "https://xhub.test/oauth/authorize"

    client.app.dependency_overrides[oauth.get_current_user] = lambda: dummy_user
    client.app.dependency_overrides[oauth.get_x_oauth_service] = (
        lambda: FakeOAuthService()
    )

    response = client.get("/api/v1/oauth/x/login")
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"authorization_url": "https://xhub.test/oauth/authorize"}
