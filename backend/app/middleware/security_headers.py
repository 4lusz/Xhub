"""Headers HTTP de seguranca aplicados a toda resposta.

Correcao (auditoria de seguranca): a aplicacao nao definia nenhum header
de seguranca -- nem `X-Frame-Options`/`frame-ancestors` (clickjacking),
nem `X-Content-Type-Options` (MIME sniffing), nem `Content-Security-Policy`
nem `Referrer-Policy`. Como o XHub e uma API pura consumida por um SPA
separado (nunca serve HTML proprio alem do `GET /` de diagnostico em
`app.main`), a politica de CSP aqui e deliberadamente restritiva
(`default-src 'none'`) -- a API nunca precisa carregar nenhum recurso
nem ser embutida em outra pagina.

Segue o mesmo padrao de `RequestContextMiddleware`/`RateLimitMiddleware`:
middleware leve, sem estado, sem dependencia externa.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_SECURITY_HEADERS = {
    # A API nunca deve ser embutida em um <iframe> de outra origem.
    "X-Frame-Options": "DENY",
    # Impede que o navegador tente "adivinhar" um Content-Type diferente
    # do declarado pela resposta (protecao contra MIME sniffing).
    "X-Content-Type-Options": "nosniff",
    # A API nao serve paginas HTML nem carrega recursos de terceiros --
    # politica restritiva por padrao, coerente com o papel da aplicacao
    # (backend puro, consumido via fetch/XHR pelo frontend em outra
    # origem, nunca renderizado diretamente no navegador).
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    # Desliga por padrao APIs de navegador sensiveis que esta aplicacao
    # nunca usa (a API nunca e renderizada como documento navegavel, mas
    # o header e barato e reforca a postura mesmo se isso mudar).
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # Por especificacao (RFC 6797), o navegador IGNORA este header
    # quando a resposta chega por HTTP puro -- seguro de manter sempre
    # presente mesmo em desenvolvimento local (sem HTTPS), e sem efeito
    # ate a aplicacao ser servida atras de HTTPS em producao.
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response
