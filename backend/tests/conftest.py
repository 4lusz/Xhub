import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database.session import get_db
from app.integrations.groq_client import GroqClient
from app.main import app


class DummyDB:
    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


@pytest.fixture(autouse=True)
def disable_startup(monkeypatch):
    monkeypatch.setattr("app.main.sync_official_plans", lambda: None)
    monkeypatch.setattr("app.main.start_scheduler", lambda: None)
    monkeypatch.setattr(GroqClient, "validate_configuration", lambda self: None)
    yield


@pytest.fixture(autouse=True)
def patch_route_databases(monkeypatch):
    dummy_db = DummyDB()
    app.dependency_overrides[get_db] = lambda: dummy_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def dummy_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.UUID(int=1),
        name="Test User",
        email="test@example.com",
        role="client",
        is_blocked=False,
        must_change_password=False,
        security_question=None,
    )
