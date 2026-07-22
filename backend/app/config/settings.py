"""
Configuracoes centrais da aplicacao.

Todas as variaveis de ambiente sao carregadas e validadas aqui via
pydantic-settings. Nenhum outro modulo deve ler os.environ diretamente --
sempre importar `settings` a partir daqui.
"""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valores de exemplo/placeholder que NUNCA podem ser usados fora do
# ambiente de desenvolvimento. Se algum destes valores estiver
# configurado com ENVIRONMENT != "development", a aplicacao recusa
# subir -- eliminar por completo a possibilidade de um segredo padrao
# chegar a producao.
_INSECURE_JWT_SECRETS = {
    "",
    "change-me-in-env",
    "troque-esta-chave-em-producao",
}
_MIN_JWT_SECRET_LENGTH = 32

# Chave Fernet valida (32 bytes urlsafe-base64) usada SOMENTE como
# default de desenvolvimento local -- e publica (este arquivo fica no
# repositorio), portanto e tratada como insegura e bloqueada em
# qualquer ENVIRONMENT != "development" pelo validator abaixo.
_DEV_ONLY_TOKEN_ENCRYPTION_KEY = "eGh1Yi1kZXYtb25seS1JTlNFQ1VSRS1rZXktMDAwMDA="

_INSECURE_TOKEN_ENCRYPTION_KEYS = {
    "",
    "change-me-in-env",
    "troque-esta-chave-em-producao",
    _DEV_ONLY_TOKEN_ENCRYPTION_KEY,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Geral
    # ------------------------------------------------------------------ #
    PROJECT_NAME: str = "XHub"
    ENVIRONMENT: str = Field(default="development")
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = Field(default=False)

    # ------------------------------------------------------------------ #
    # Banco de dados
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://xhub:xhub@db:5432/xhub"
    )

    # ------------------------------------------------------------------ #
    # JWT / Auth (usado a partir da proxima etapa, ja deixamos preparado)
    # ------------------------------------------------------------------ #
    JWT_SECRET_KEY: str = Field(default="change-me-in-env")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # ------------------------------------------------------------------ #
    # Criptografia de tokens OAuth em repouso (Fernet -- AES128-CBC +
    # HMAC-SHA256 autenticado). Chave simetrica de 32 bytes urlsafe-
    # base64 (gerar com `Fernet.generate_key()`), lida via variavel de
    # ambiente. Nunca deve ter valor padrao utilizavel em producao (ver
    # `_validate_production_secrets` abaixo).
    # ------------------------------------------------------------------ #
    TOKEN_ENCRYPTION_KEY: str = Field(default=_DEV_ONLY_TOKEN_ENCRYPTION_KEY)

    # ------------------------------------------------------------------ #
    # OAuth2 do X (Twitter) -- usado a partir da etapa de contas
    # ------------------------------------------------------------------ #
    X_CLIENT_ID: str = Field(default="")
    X_CLIENT_SECRET: str = Field(default="")
    X_CALLBACK_URL: str = Field(
        default="http://localhost:8000/api/v1/oauth/x/callback"
    )
    # `media.write` foi adicionado para permitir o upload de midia
    # (imagem/gif/video) em nome do usuario via
    # `POST https://api.x.com/2/media/upload` -- ver
    # docs/ROADMAP_MEDIA.md. Contas conectadas ANTES desta mudanca nao
    # tem esse escopo concedido e precisam ser reconectadas para
    # publicar posts com midia (o escopo e definido no momento da
    # autorizacao no X, nao pode ser adicionado retroativamente a um
    # token ja emitido).
    X_OAUTH_SCOPES: str = Field(
        default="tweet.read tweet.write users.read offline.access media.write"
    )
    FRONTEND_URL: str = Field(default="http://localhost:5173")
    BACKEND_URL: str = Field(default="http://localhost:8000")

    # ------------------------------------------------------------------ #
    # Rate limiting simples para rotas sensiveis de auth
    # ------------------------------------------------------------------ #
    AUTH_RATE_LIMIT_ENABLED: bool = Field(default=True)
    AUTH_RATE_LIMIT_MAX_REQUESTS: int = Field(default=10)
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)
    # Confianca em X-Forwarded-For: por padrao (False) o rate limit usa
    # exclusivamente o IP de conexao TCP (request.client.host), que nao
    # pode ser forjado pelo cliente. So deve ser habilitado quando a
    # aplicacao roda atras de um proxy/load balancer confiavel que
    # reescreve esse header (nunca repassa o valor recebido do cliente
    # sem sobrescrever) -- ver `RateLimitMiddleware._client_key`.
    TRUST_PROXY_HEADERS: bool = Field(default=False)

    # ------------------------------------------------------------------ #
    # Agendamento de posts (worker in-process via APScheduler)
    # ------------------------------------------------------------------ #
    SCHEDULER_ENABLED: bool = Field(default=True)
    SCHEDULER_INTERVAL_SECONDS: int = Field(default=30)
    SCHEDULER_BATCH_SIZE: int = Field(default=25)

    # ------------------------------------------------------------------ #
    # Publicacao Inteligente -- integracao com a Groq para geracao de
    # variacoes naturais de texto entre publicacoes (ver
    # docs/ROADMAP_PUBLICACAO_INTELIGENTE.md). O roadmap oficial exige
    # o uso da Groq e proibe explicitamente o uso da OpenAI para esta
    # funcionalidade.
    # ------------------------------------------------------------------ #
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    GROQ_TIMEOUT_SECONDS: int = Field(default=15)
    AI_CONTENT_VARIATION_PROMPT_VERSION: str = Field(default="v1")
    INTELLIGENT_PUBLICATION_CACHE_ENABLED: bool = Field(default=True)
    INTELLIGENT_PUBLICATION_CACHE_TTL_SECONDS: int = Field(default=600)
    # Numero maximo de variacoes pedidas a Groq em UMA UNICA chamada
    # (analise de escalabilidade -- clientes com muitas contas
    # conectadas, ver docs/ROADMAP_JITTER.md/claude.md). Pedir todas as
    # variacoes de uma vez so (ex.: 100 para um post com 100 contas)
    # arrisca estourar `GROQ_TIMEOUT_SECONDS` e degrada a diversidade
    # das variacoes geradas. `AIContentVariationService` divide
    # automaticamente qualquer pedido maior que este valor em multiplas
    # chamadas sequenciais menores, sem mudar o resultado final nem o
    # comportamento para o caso comum (ate poucas dezenas de contas).
    AI_CONTENT_VARIATION_MAX_BATCH_SIZE: int = Field(default=20)

    # ------------------------------------------------------------------ #
    # Midia (imagem/gif/video) anexada a posts -- ver
    # docs/ROADMAP_MEDIA.md. Limites de tamanho/combinacao por tipo
    # ficam em `app.domain.media_rules` (regra de negocio pura); aqui
    # apenas configuracao de infraestrutura (onde gravar em disco, como
    # falar com o endpoint de upload de midia do X).
    # ------------------------------------------------------------------ #
    MEDIA_STORAGE_DIR: str = Field(default="media_storage")
    X_MEDIA_UPLOAD_CHUNK_SIZE_BYTES: int = Field(default=4 * 1024 * 1024)
    X_MEDIA_UPLOAD_TIMEOUT_SECONDS: float = Field(default=30.0)
    X_MEDIA_STATUS_MAX_WAIT_SECONDS: int = Field(default=90)

    # ------------------------------------------------------------------ #
    # Jitter -- atraso aleatorio aplicado ENTRE publicacoes em contas
    # diferentes de um mesmo post, para tornar a sequencia de chamadas a
    # API do X menos automatizada (ver docs/ROADMAP_JITTER.md). Estes
    # dois valores sao usados APENAS como seed inicial da linha unica de
    # `jitter_settings` no banco, na primeira leitura (ver
    # `JitterSettingsRepository.get_or_create_default`) -- depois disso,
    # o administrador controla os valores em uso via
    # `PATCH /admin/jitter-settings`, sem exigir mudanca de codigo nem
    # reinicio da aplicacao.
    # ------------------------------------------------------------------ #
    JITTER_DEFAULT_MIN_SECONDS: float = Field(default=1.5)
    JITTER_DEFAULT_MAX_SECONDS: float = Field(default=8.0)
    # Teto de seguranca para o valor MAXIMO configuravel pelo
    # administrador (validado em `JitterService.update_settings`) --
    # evita que um valor digitado por engano (ex.: 600 em vez de 6.0)
    # torne uma publicacao em varias contas absurdamente lenta a ponto
    # de estourar timeout do navegador/proxy na chamada sincrona de
    # `POST /posts/{id}/publish`.
    JITTER_MAX_ALLOWED_SECONDS: float = Field(default=120.0)

    # ------------------------------------------------------------------ #
    # Metricas de desempenho (tela "Resultados" -- ver
    # docs/ROADMAP_METRICAS.md). Le dados reais da API do X (impressoes,
    # curtidas, seguidores), que e paga por uso -- ao contrario de
    # publicar (ja incluido no custo do plano), CADA coleta tem custo
    # direto. `METRICS_POST_RETENTION_DAYS` limita a coleta a posts
    # publicados recentemente (a maior parte do alcance de um post
    # acontece nas primeiras 24-48h), controlando o custo agregado --
    # posts mais antigos que a janela simplesmente param de ganhar
    # snapshots novos, mas o ultimo valor coletado nunca e apagado.
    # ------------------------------------------------------------------ #
    METRICS_COLLECTION_ENABLED: bool = Field(default=True)
    METRICS_COLLECTION_INTERVAL_SECONDS: int = Field(default=6 * 60 * 60)
    METRICS_POST_RETENTION_DAYS: int = Field(default=14)
    # Janela usada para calcular a media historica de alcance de uma
    # conta (deteccao de anomalia, ver app.domain.metrics) -- pode olhar
    # mais pra tras que a janela de coleta acima, ja que o ULTIMO
    # snapshot de um post antigo continua no banco mesmo apos ele parar
    # de ser recoletado.
    METRICS_ANOMALY_LOOKBACK_DAYS: int = Field(default=90)
    METRICS_ANOMALY_RECENT_WINDOW: int = Field(default=5)
    METRICS_ANOMALY_MIN_TOTAL_POSTS: int = Field(default=8)
    METRICS_ANOMALY_DROP_THRESHOLD: float = Field(default=0.5)

    # Compatibilidade com nomes antigos usados nas etapas iniciais.
    TWITTER_CLIENT_ID: str = Field(default="")
    TWITTER_CLIENT_SECRET: str = Field(default="")
    TWITTER_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/v1/oauth/twitter/callback"
    )

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:5173"])

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Elimina por completo a possibilidade de segredos padrao/fracos
        chegarem a producao. So se aplica quando ENVIRONMENT != "development",
        para nao quebrar o ambiente local de desenvolvimento."""
        if self.ENVIRONMENT.strip().lower() == "development":
            return self

        if (
            self.JWT_SECRET_KEY in _INSECURE_JWT_SECRETS
            or len(self.JWT_SECRET_KEY) < _MIN_JWT_SECRET_LENGTH
        ):
            raise ValueError(
                "JWT_SECRET_KEY invalido ou ausente para ENVIRONMENT="
                f"'{self.ENVIRONMENT}'. Defina uma chave secreta forte "
                f"(minimo {_MIN_JWT_SECRET_LENGTH} caracteres, gerada "
                "aleatoriamente) na variavel de ambiente JWT_SECRET_KEY. "
                "Nunca utilize o valor de exemplo do .env.example fora "
                "do ambiente de desenvolvimento."
            )

        if self.TOKEN_ENCRYPTION_KEY in _INSECURE_TOKEN_ENCRYPTION_KEYS:
            raise ValueError(
                "TOKEN_ENCRYPTION_KEY invalido ou ausente para ENVIRONMENT="
                f"'{self.ENVIRONMENT}'. Defina uma chave Fernet valida "
                "(gerada com `Fernet.generate_key()`) na variavel de "
                "ambiente TOKEN_ENCRYPTION_KEY."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna a instancia (cacheada) de Settings."""
    return Settings()


settings = get_settings()
