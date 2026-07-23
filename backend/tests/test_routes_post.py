import uuid
from types import SimpleNamespace

from app.routes import post


def test_get_scheduled_post_returns_scheduled_post(client):
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000005")
    post_id = uuid.UUID("00000000-0000-0000-0000-000000000006")
    scheduled_for = "2026-01-01T12:00:00Z"
    dummy_user = SimpleNamespace(id=user_id)

    class FakePostService:
        def get_post(self, _post_id: uuid.UUID) -> SimpleNamespace:
            assert _post_id == post_id
            return SimpleNamespace(user_id=user_id)

    class FakeScheduledPostService:
        def get_by_post(self, _post_id: uuid.UUID) -> SimpleNamespace:
            assert _post_id == post_id
            return SimpleNamespace(
                id=uuid.UUID("00000000-0000-0000-0000-000000000007"),
                post_id=post_id,
                scheduled_for=scheduled_for,
                executed=False,
                attempts=0,
                last_error=None,
            )

    client.app.dependency_overrides[post.get_current_user] = lambda: dummy_user
    client.app.dependency_overrides[post.get_post_service] = lambda: FakePostService()
    client.app.dependency_overrides[post.get_scheduled_post_service] = (
        lambda: FakeScheduledPostService()
    )

    response = client.get(f"/api/v1/posts/{post_id}/schedule")
    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": "00000000-0000-0000-0000-000000000007",
        "post_id": str(post_id),
        "scheduled_for": "2026-01-01T12:00:00Z",
        "executed": False,
        "attempts": 0,
        "last_error": None,
    }


def test_get_post_blocks_idor_from_another_user(client):
    """Auditoria de seguranca -- item 7 (IDOR): usuario A autenticado
    nao pode ler um post que pertence ao usuario B trocando o id na
    requisicao -- `GET /posts/{post_id}` deve responder 403, nunca o
    conteudo do post de outro usuario."""
    owner_id = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
    requester_id = uuid.UUID("00000000-0000-0000-0000-0000000000bb")
    post_id = uuid.UUID("00000000-0000-0000-0000-0000000000cc")

    class FakePostService:
        def get_post(self, _post_id: uuid.UUID) -> SimpleNamespace:
            assert _post_id == post_id
            return SimpleNamespace(user_id=owner_id)

    client.app.dependency_overrides[post.get_current_user] = lambda: SimpleNamespace(
        id=requester_id
    )
    client.app.dependency_overrides[post.get_post_service] = lambda: FakePostService()

    response = client.get(f"/api/v1/posts/{post_id}")
    client.app.dependency_overrides.clear()

    assert response.status_code == 403


def test_delete_post_blocks_idor_from_another_user(client):
    """Mesma checagem de posse, agora numa operacao destrutiva
    (`DELETE /posts/{post_id}`) -- usuario A nao pode excluir post do
    usuario B."""
    owner_id = uuid.UUID("00000000-0000-0000-0000-0000000000dd")
    requester_id = uuid.UUID("00000000-0000-0000-0000-0000000000ee")
    post_id = uuid.UUID("00000000-0000-0000-0000-0000000000ff")

    class FakePostService:
        def get_post(self, _post_id: uuid.UUID) -> SimpleNamespace:
            assert _post_id == post_id
            return SimpleNamespace(user_id=owner_id)

        def delete_post(self, _post_id: uuid.UUID) -> None:
            raise AssertionError("delete_post nunca deveria ser chamado (IDOR)")

    client.app.dependency_overrides[post.get_current_user] = lambda: SimpleNamespace(
        id=requester_id
    )
    client.app.dependency_overrides[post.get_post_service] = lambda: FakePostService()

    response = client.delete(f"/api/v1/posts/{post_id}")
    client.app.dependency_overrides.clear()

    assert response.status_code == 403
