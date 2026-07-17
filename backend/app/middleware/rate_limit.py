"""Rate limiting simples para endpoints sensiveis de autenticacao.

Correcoes (auditoria itens 6 e 7):

1. `X-Forwarded-For` deixou de ser confiavel por padrao. Um cliente
   pode enviar qualquer valor nesse header, entao usa-lo cegamente para
   chavear o rate limit permite contornar o limite trivialmente
   (bastando variar o header a cada requisicao). Agora o IP usado e
   sempre `request.client.host` (a conexao TCP real, que o cliente nao
   controla), a menos que `settings.TRUST_PROXY_HEADERS` esteja
   explicitamente habilitado -- opcao que so deve ser ligada quando a
   aplicacao roda atras de um proxy/load balancer confiavel que
   *sobrescreve* (nunca repassa) esse header.
2. O dicionario de tentativas em memoria (`self._requests`) nunca
   removia chaves cujo deque esvaziou -- crescia indefinidamente sob
   trafego sustentado. Duas limpezas agora coexistem:
   a) por-chave, logo apos processar uma requisicao daquela chave (cobre
      o caso comum de clientes que continuam batendo no mesmo endpoint);
   b) uma varredura periodica de TODO o dicionario a cada
      `_CLEANUP_SWEEP_INTERVAL` requisicoes, que remove chaves cujas
      entradas ja expiraram e cujo cliente nunca mais voltou a fazer
      requisicoes -- sem essa varredura, uma chave "de uma vez so"
      (ex.: um IP que tentou logar uma unica vez e nunca mais voltou)
      ficaria ocupando memoria indefinidamente, pois nada mais a tocaria
      para disparar a limpeza por-chave.

Observacao mantida da auditoria (item 7): este mecanismo continua em
memoria local por processo, portanto o limite efetivo e por-processo,
nao global -- com multiplos workers/replicas o limite agregado sera
maior que `AUTH_RATE_LIMIT_MAX_REQUESTS`. Resolver isso definitivamente
exigiria estado compartilhado (ex.: Redis), o que nao faz parte do
escopo desta correcao para nao introduzir infraestrutura nova sem
necessidade real comprovada; o memory leak e a falha de spoofing, que
eram os problemas de severidade mais alta, estao corrigidos aqui.

Correcao (auditoria de seguranca -- flood/DoS): a cobertura deste
middleware era estrita demais (somente `/auth/login`), deixando sem
nenhuma protecao endpoints sensiveis explicitamente exploraveis por um
atacante autenticado com uma unica conta valida: geracao de preview da
Publicacao Inteligente (custo real por chamada a Groq -- variar
minimamente o texto a cada requisicao contorna o cache em memoria e
forca uma chamada paga a cada tentativa), upload de midia (ate 512MB
por arquivo, sem cota de armazenamento por usuario -- upload repetido
esgota disco), login/renovacao de sessao, inicio do fluxo OAuth do X, e
publicacao/agendamento de posts. Estendido para cobrir esses caminhos
(estaticos e dinamicos, ver `_is_rate_limited_path`), reaproveitando
exatamente a mesma infraestrutura (mesma janela deslizante em memoria,
mesmas configuracoes `AUTH_RATE_LIMIT_*`) -- cada caminho continua tendo
seu proprio orcamento independente, pois a chave ja inclui o path (ver
`_client_key`, agora tambem com o metodo HTTP, para nao acoplar leituras
e escritas no mesmo endpoint sob o mesmo orcamento).

Endpoints deliberadamente NAO incluidos, com justificativa: `POST
/admin/users` (criacao de usuario) exige um JWT de administrador valido
-- inacessivel a um atacante com "acesso apenas ao frontend e a API
publica" (fora do modelo de ameaca desta correcao); nao ha
`POST /auth/register` (auto cadastro nunca existiu nesta aplicacao, ver
`app.routes.auth`), entao "spam de criacao de usuarios" por um atacante
anonimo nao se aplica.
"""

import re
from collections import defaultdict, deque
from time import monotonic
from typing import Deque

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.config.settings import settings

# A cada N requisicoes processadas por este middleware (em qualquer
# chave), o dicionario inteiro e varrido em busca de chaves totalmente
# expiradas. Nao precisa ser exato -- o objetivo e apenas limitar o
# crescimento maximo do dicionario a uma janela de tempo, mesmo para
# clientes que fazem uma unica leva de requisicoes e nunca mais voltam.
_CLEANUP_SWEEP_INTERVAL = 500

# UUID no formato padrao (com hifens) -- unico formato aceito pelos
# path params `uuid.UUID` do FastAPI nas rotas abaixo.
_UUID_SEGMENT = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._requests: dict[str, Deque[float]] = defaultdict(deque)
        self._requests_processed = 0

        prefix = settings.API_V1_PREFIX
        # Caminhos estaticos (sem path param) -- comparados por igualdade.
        self._static_rate_limited_paths = {
            f"{prefix}/auth/login",
            f"{prefix}/auth/refresh",
            f"{prefix}/intelligent-publication/preview",
            f"{prefix}/media/upload",
            f"{prefix}/oauth/x/login",
        }
        # Caminhos com path param (`{post_id}`) -- comparados por regex,
        # ja que o valor real do UUID varia a cada requisicao.
        self._dynamic_rate_limited_patterns = [
            re.compile(rf"^{re.escape(prefix)}/posts/{_UUID_SEGMENT}/publish$"),
            re.compile(rf"^{re.escape(prefix)}/posts/{_UUID_SEGMENT}/schedule$"),
        ]

    def _is_rate_limited_path(self, path: str) -> bool:
        if path in self._static_rate_limited_paths:
            return True
        return any(pattern.match(path) for pattern in self._dynamic_rate_limited_patterns)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.AUTH_RATE_LIMIT_ENABLED or not self._is_rate_limited_path(
            request.url.path
        ):
            return await call_next(request)

        key = self._client_key(request)
        now = monotonic()
        window_start = now - settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
        attempts = self._requests[key]

        self._evict_expired(attempts, window_start)

        if len(attempts) >= settings.AUTH_RATE_LIMIT_MAX_REQUESTS:
            if not attempts:
                self._requests.pop(key, None)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Muitas tentativas. Tente novamente em instantes."},
                headers={"Retry-After": str(settings.AUTH_RATE_LIMIT_WINDOW_SECONDS)},
            )

        attempts.append(now)
        self._requests_processed += 1

        if self._requests_processed % _CLEANUP_SWEEP_INTERVAL == 0:
            self._sweep_stale_keys(window_start)

        try:
            return await call_next(request)
        finally:
            if not attempts:
                self._requests.pop(key, None)

    def _evict_expired(self, attempts: Deque[float], window_start: float) -> None:
        while attempts and attempts[0] <= window_start:
            attempts.popleft()

    def _sweep_stale_keys(self, window_start: float) -> None:
        stale_keys = []
        for key, attempts in self._requests.items():
            self._evict_expired(attempts, window_start)
            if not attempts:
                stale_keys.append(key)

        for key in stale_keys:
            self._requests.pop(key, None)

    def _client_key(self, request: Request) -> str:
        host = request.client.host if request.client else "unknown"

        if settings.TRUST_PROXY_HEADERS:
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                host = forwarded_for.split(",", 1)[0].strip() or host

        return f"{request.method}:{request.url.path}:{host}"