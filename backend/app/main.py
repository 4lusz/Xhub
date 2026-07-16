"""
Entrypoint da aplicacao XHub API.

Correcoes desta etapa (ver CHANGELOG.md para detalhes):
- Logging estruturado + tratamento global de excecoes (auditoria item 4).
- Bootstrap automatico do catalogo de planos no startup (auditoria item 1).
- Inicializacao/finalizacao do worker de agendamento de posts (auditoria
  item 3).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.core.bootstrap import sync_official_plans
from app.core.logging_config import configure_logging, get_logger
from app.integrations.groq_client import GroqClient
from app.routes import admin, auth, health, oauth, twitter_account
from app.routes import intelligent_publication, media, me, post
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.scheduler import shutdown_scheduler, start_scheduler

configure_logging(debug=settings.DEBUG)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante que a aplicacao suba operacional (com o catalogo oficial
    # de planos disponivel) sem exigir nenhuma intervencao manual no
    # banco -- ver `app.core.bootstrap`.
    sync_official_plans()
    GroqClient().validate_configuration()
    start_scheduler()

    logger.info("XHub API iniciada.", extra={"environment": settings.ENVIRONMENT})

    yield

    shutdown_scheduler()
    logger.info("XHub API finalizada.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

# Adicionado por ultimo de proposito: no Starlette, o middleware
# adicionado por ultimo se torna o mais externo (o primeiro a executar
# na entrada da requisicao). Precisamos que o `request_id` de
# correlacao ja exista ANTES de qualquer outro middleware/rota rodar,
# para que TODO log emitido durante o processamento da requisicao
# (incluindo dentro do rate limiter e do CORS) possa ser correlacionado.
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler global de excecoes (auditoria item 4).

    Antes desta correcao, qualquer excecao nao tratada (erro de rede
    com a API do X, erro de banco, bug de programacao) virava um 500
    generico do proprio Starlette e desaparecia sem deixar nenhum
    rastro -- sem log, sem correlation-id, sem stacktrace. Este handler
    garante que toda excecao nao tratada seja registrada (com
    stacktrace completo e o `request_id` de correlacao da requisicao,
    ver `app.middleware.request_context`) antes de responder ao
    cliente, sem nunca vazar detalhes internos (mensagem de excecao,
    stacktrace) no corpo da resposta HTTP.
    """
    logger.exception(
        "Excecao nao tratada.",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno do servidor."},
    )


app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(me.router, prefix=settings.API_V1_PREFIX)
app.include_router(oauth.router, prefix=settings.API_V1_PREFIX)
app.include_router(twitter_account.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(post.router, prefix=settings.API_V1_PREFIX)
app.include_router(media.router, prefix=settings.API_V1_PREFIX)
app.include_router(intelligent_publication.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root() -> dict:
    return {"service": settings.PROJECT_NAME, "status": "running"}

