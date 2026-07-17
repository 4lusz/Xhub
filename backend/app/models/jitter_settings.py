"""Model JitterSettings -- configuracao administrativa do atraso (jitter)
aplicado entre publicacoes em contas diferentes de um mesmo post.

Tabela "singleton": existe sempre EXATAMENTE uma linha, criada sob
demanda com os valores padrao (`settings.JITTER_DEFAULT_MIN_SECONDS`/
`JITTER_DEFAULT_MAX_SECONDS`) na primeira leitura, se ainda nao existir
(ver `JitterSettingsRepository.get_or_create_default`). Nenhum outro
lugar do codigo deve ter os limites de min/max fixos -- toda leitura
passa por esta tabela (ver docs/ROADMAP_JITTER.md).
"""

import uuid

from sqlalchemy import Float
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class JitterSettings(TimestampMixin, Base):
    __tablename__ = "jitter_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    min_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    max_seconds: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:
        return f"<JitterSettings min={self.min_seconds} max={self.max_seconds}>"
