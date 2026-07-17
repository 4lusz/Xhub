"""Repository para o model JitterSettings (configuracao singleton)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.jitter_settings import JitterSettings
from app.repositories.base import BaseRepository


class JitterSettingsRepository(BaseRepository[JitterSettings]):
    """Acesso a linha unica de configuracao do Jitter."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, JitterSettings)

    def get_or_create_default(self) -> JitterSettings:
        """Retorna a linha unica de configuracao, criando-a com os
        valores padrao (`settings.JITTER_DEFAULT_MIN_SECONDS`/
        `JITTER_DEFAULT_MAX_SECONDS`) na primeira leitura, se ainda nao
        existir. `order_by(created_at)` + `limit(1)` torna a leitura
        deterministica mesmo na hipotese remota de mais de uma linha
        existir (ex.: uma corrida rara na primeira criacao)."""
        statement = select(JitterSettings).order_by(JitterSettings.created_at).limit(1)
        existing = self.db.scalars(statement).first()

        if existing is not None:
            return existing

        return self.create(
            {
                "min_seconds": settings.JITTER_DEFAULT_MIN_SECONDS,
                "max_seconds": settings.JITTER_DEFAULT_MAX_SECONDS,
            }
        )
