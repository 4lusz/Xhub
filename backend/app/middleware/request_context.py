"""Correlation-id de requisicao para logging estruturado.

Correcao critica (auditoria item 4 - observabilidade): sem um
identificador de requisicao, nao ha como correlacionar as varias linhas
de log emitidas durante o processamento de uma unica requisicao (ou o
relato de um cliente) com o que aconteceu no servidor. Este middleware
gera (ou reaproveita, se o cliente/proxy enviar) um `X-Request-ID`,
guarda em uma `contextvar` (acessivel de qualquer lugar do codigo, sem
precisar repassar o valor explicitamente por todas as camadas) e o
devolve no header da resposta.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id_ctx_var: ContextVar[str | None] = ContextVar(
    "request_id", default=None
)

REQUEST_ID_HEADER = "X-Request-ID"


def get_request_id() -> str | None:
    return _request_id_ctx_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Atribui um request_id de correlacao a cada requisicao."""

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_id = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming_id.strip() if incoming_id else str(uuid.uuid4())

        token = _request_id_ctx_var.set(request_id)
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        finally:
            _request_id_ctx_var.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
