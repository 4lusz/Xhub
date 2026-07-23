import uuid
from types import SimpleNamespace

from jose import jwt as jose_jwt

from app.auth import dependencies as auth_dependencies
from app.auth.jwt import create_access_token
from app.models.enums import UserRole
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


def _build_real_user() -> SimpleNamespace:
    """Diferente da fixture `dummy_user` (que tem `role` como string
    solta, pensada para testes que sobrescrevem `get_current_user`
    inteiro): estes dois testes exercitam o caminho REAL de
    `get_current_user`/`_resolve_authenticated_user`/`_to_user_context`,
    que exige `role` como `UserRole` de verdade (`DomainUserRole(user.role.value)`)."""
    return SimpleNamespace(
        id=uuid.UUID(int=42),
        name="Real Path User",
        email="real-path@example.com",
        role=UserRole.CLIENT,
        is_blocked=False,
        must_change_password=False,
        security_question=None,
    )


def test_revoked_access_token_is_rejected_with_401(client):
    """Auditoria de seguranca -- item 4 (JWT): um access token cujo
    `jti` esta na denylist (ver `AuthService.revoke_access_token`,
    chamado no logout) nunca deve continuar sendo aceito, mesmo com
    assinatura e expiracao validas -- exercita o caminho REAL de
    `get_current_user`/`_resolve_authenticated_user` (nao mockado),
    sobrescrevendo so os repositories de dados."""
    user = _build_real_user()
    token = create_access_token(str(user.id))
    jti = jose_jwt.get_unverified_claims(token)["jti"]

    class FakeUserService:
        def get_user(self, user_id: uuid.UUID) -> SimpleNamespace:
            return user

    class FakeRevokedAccessTokenRepository:
        def is_revoked(self, checked_jti: uuid.UUID) -> bool:
            return str(checked_jti) == jti

    client.app.dependency_overrides[auth_dependencies.get_user_service] = (
        lambda: FakeUserService()
    )
    client.app.dependency_overrides[
        auth_dependencies.get_revoked_access_token_repository
    ] = lambda: FakeRevokedAccessTokenRepository()

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    client.app.dependency_overrides.clear()

    assert response.status_code == 401


def test_non_revoked_access_token_still_accepted(client):
    """Contraprova do teste acima: um token com `jti` que NAO esta na
    denylist continua sendo aceito normalmente -- garante que a
    checagem nova nao rejeita tokens validos por engano."""
    user = _build_real_user()
    token = create_access_token(str(user.id))

    class FakeUserService:
        def get_user(self, user_id: uuid.UUID) -> SimpleNamespace:
            return user

    class FakeRevokedAccessTokenRepository:
        def is_revoked(self, checked_jti: uuid.UUID) -> bool:
            return False

    client.app.dependency_overrides[auth_dependencies.get_user_service] = (
        lambda: FakeUserService()
    )
    client.app.dependency_overrides[
        auth_dependencies.get_revoked_access_token_repository
    ] = lambda: FakeRevokedAccessTokenRepository()

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
