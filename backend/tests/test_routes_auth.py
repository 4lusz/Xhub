import uuid
from types import SimpleNamespace

from app.routes import auth


def test_login_returns_token_pair(client):
    class FakeAuthService:
        def authenticate(self, *, email: str, password: str) -> SimpleNamespace:
            assert email == "test@example.com"
            assert password == "secret"
            return SimpleNamespace(
                id=uuid.UUID(int=1),
                must_change_password=False,
                security_question=None,
            )

        def requires_second_factor(self, user: SimpleNamespace) -> bool:
            return user.security_question is not None

        def create_access_token(self, user: SimpleNamespace) -> str:
            assert user.id == uuid.UUID(int=1)
            return "access-token"

        def issue_refresh_token(self, user: SimpleNamespace) -> str:
            assert user.id == uuid.UUID(int=1)
            return "refresh-token"

    client.app.dependency_overrides[auth.get_auth_service] = lambda: FakeAuthService()
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "secret"},
    )
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
        "must_change_password": False,
    }


def test_get_current_user_profile_returns_user(client, dummy_user):
    class FakeUserService:
        def get_user(self, user_id: uuid.UUID) -> SimpleNamespace:
            assert user_id == dummy_user.id
            return dummy_user

    client.app.dependency_overrides[auth.get_current_user] = lambda: dummy_user
    client.app.dependency_overrides[auth.get_user_service] = lambda: FakeUserService()

    response = client.get("/api/v1/auth/me")
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": str(dummy_user.id),
        "name": dummy_user.name,
        "email": dummy_user.email,
        "role": dummy_user.role,
        "is_blocked": dummy_user.is_blocked,
        "must_change_password": dummy_user.must_change_password,
        "security_question": dummy_user.security_question,
    }
