"""Testes do RateLimitMiddleware (auditoria de seguranca -- item 1).

App isolado (so o middleware + uma rota falsa no mesmo path real de
login), para nao herdar estado do app principal nem de outros testes
que tambem chamam /auth/login.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config.settings import settings
from app.middleware.rate_limit import RateLimitMiddleware


def _build_test_app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware)

    @test_app.post(f"{settings.API_V1_PREFIX}/auth/login")
    def fake_login() -> dict:
        return {"ok": True}

    return test_app


def test_rate_limit_blocks_after_max_requests(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 3)
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_MAX_REQUESTS", 3)
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_WINDOW_SECONDS", 60)

    client = TestClient(_build_test_app())

    statuses = [
        client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            data={"username": "alvo-teste@exemplo.com", "password": "x"},
        ).status_code
        for _ in range(5)
    ]

    # As 3 primeiras (limite configurado) passam; a partir da 4a, 429.
    assert statuses[:3] == [200, 200, 200]
    assert statuses[3] == 429
    assert statuses[4] == 429


def test_rate_limit_per_target_blocks_even_with_different_ip_header(monkeypatch):
    """Mesmo alvo (e-mail submetido), IPs diferentes -- a dimensao por
    alvo bloqueia de qualquer forma (ver docstring de
    app.middleware.rate_limit sobre a correcao de credential stuffing
    via rotacao de IP)."""
    monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 2)
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_MAX_REQUESTS", 1000)
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)

    client = TestClient(_build_test_app())

    statuses = []
    for index in range(4):
        response = client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            data={"username": "mesmo-alvo@exemplo.com", "password": "x"},
            headers={"X-Forwarded-For": f"10.0.0.{index}"},
        )
        statuses.append(response.status_code)

    assert statuses[:2] == [200, 200]
    assert statuses[2] == 429
    assert statuses[3] == 429
