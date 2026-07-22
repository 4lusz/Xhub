"""Model AccountMetricSnapshot -- serie historica de metricas de conta.

Append-only, assim como `AuditLog` (ver
`AccountMetricSnapshotRepository`, que bloqueia update/delete pelo
mesmo motivo): cada coleta periodica insere uma linha nova, nunca
sobrescreve uma anterior -- e a serie temporal completa que alimenta o
grafico de seguidores ao longo do tempo na tela de Resultados. So
existe `collected_at` (fixado na insercao), sem `updated_at`.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.twitter_account import TwitterAccount


class AccountMetricSnapshot(Base):
    __tablename__ = "account_metric_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    twitter_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("twitter_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # `None` quando a API do X nao retornou o campo nesta coleta (ex.:
    # falha parcial) -- nunca gravamos zero como substituto de "sem dado".
    followers_count: Mapped[int | None] = mapped_column(nullable=True)

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    twitter_account: Mapped["TwitterAccount"] = relationship()

    def __repr__(self) -> str:
        return f"<AccountMetricSnapshot twitter_account_id={self.twitter_account_id} collected_at={self.collected_at}>"
