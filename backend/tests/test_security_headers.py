"""Testes do SecurityHeadersMiddleware (auditoria de seguranca -- item 6)."""


def test_security_headers_present_on_every_response(client):
    response = client.get("/api/v1/health")

    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "strict-transport-security" in response.headers
    assert response.headers["referrer-policy"] == "no-referrer"


def test_security_headers_present_even_on_error_response(client):
    """Os headers devem estar presentes tambem em respostas de erro
    (ex.: 404), nao so no caminho feliz -- confirma que o middleware
    roda para toda resposta, independente do status."""
    response = client.get("/api/v1/rota-que-nao-existe")

    assert response.status_code == 404
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
