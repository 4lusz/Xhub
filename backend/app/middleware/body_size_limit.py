"""Limite de tamanho do corpo de requisicoes JSON/form comuns.

Correcao (auditoria de seguranca -- "payloads gigantes"): o FastAPI/
Starlette nao impoe nenhum limite de tamanho de corpo por padrao --
`Request.body()` (usado internamente para popular um schema Pydantic)
le e concatena o corpo inteiro em memoria ANTES de qualquer validacao
de campo (`max_length`, etc.) rodar. Um cliente podia enviar um corpo
JSON de centenas de megabytes (ex.: um campo `text` gigantesco) e o
processo bufferizava tudo antes de rejeitar com 422 -- desperdicio de
memoria/CPU proporcional ao tamanho do ataque, mesmo a requisicao sendo
sempre invalida no fim.

Este middleware rejeita (413) requisicoes cujo `Content-Length`
declarado exceda `_MAX_JSON_BODY_BYTES` ANTES de qualquer leitura do
corpo -- o valor cobre com folga o maior payload JSON legitimo da
aplicacao (post de 280 caracteres + ate `MAX_ACCOUNTS_ACROSS_PLANS`
UUIDs + textos finais da Publicacao Inteligente por conta).

Rotas multipart (`POST /media/upload`) sao explicitamente excluidas:
ja tem seu proprio limite, maior e por tipo de midia, aplicado em
streaming por `app.core.media_storage.save_upload` (nunca carrega o
arquivo inteiro em memoria) -- um teto fixo aqui as quebraria.

Limitacao aceita: um cliente que omite `Content-Length` e usa
`Transfer-Encoding: chunked` contorna esta checagem (que so inspeciona o
header, nunca bufferiza para contar bytes de verdade, para nao
reintroduzir o mesmo problema que esta correcao resolve). Mitigacao
completa desse caso exige um limite na camada de proxy reverso (ex.:
`client_max_body_size` do Nginx) na frente da aplicacao em producao --
fora do escopo de codigo da aplicacao em si.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# 1 MiB: generoso para qualquer payload JSON legitimo da aplicacao (o
# maior caso real -- criacao de post com textos finais da Publicacao
# Inteligente para o maior plano -- fica na casa de dezenas de KB).
_MAX_JSON_BODY_BYTES = 1 * 1024 * 1024

_EXEMPT_CONTENT_TYPE_PREFIXES = ("multipart/form-data",)


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        content_type = request.headers.get("content-type", "")
        if content_type.lower().startswith(_EXEMPT_CONTENT_TYPE_PREFIXES):
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = None

            if declared_size is not None and declared_size > _MAX_JSON_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Corpo da requisicao excede o tamanho maximo permitido."},
                )

        return await call_next(request)
