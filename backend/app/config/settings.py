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
    X_OAUTH_SCOPES: str = Field(default="tweet.read tweet.write users.read offline.access")
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
