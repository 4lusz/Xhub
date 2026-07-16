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
