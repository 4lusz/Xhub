"""Model PostMetricSnapshot -- serie historica de metricas de um tweet.

Uma linha por coleta, por `PostAccount` (um tweet publicado numa conta
especifica) -- append-only, mesmo principio de `AccountMetricSnapshot`/
`AuditLog`: nunca sobrescreve, sempre insere, formando a curva de vida
do tweet (visualizacoes/curtidas ao longo do tempo desde a publicacao).

`twitter_account_id` e denormalizado a partir de
`PostAccount.twitter_account_id` no momento da coleta -- nunca a fonte
da verdade sobre essa relacao (que continua em `PostAccount`), apenas um
atalho de leitura para a consulta mais comum desta tabela ("todas as
metricas de posts de uma conta, num periodo"), que senao exigiria JOIN
em toda leitura do portfolio.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.post_account import PostAccount
    from app.models.twitter_account import TwitterAccount


class PostMetricSnapshot(Base):
    __tablename__ = "post_metric_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("post_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    twitter_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("twitter_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Todos nullable: a API do X pode nao autorizar `organic_metrics`
    # (impressoes) para o tier/app atual mesmo com o token correto -- a
    # coleta nunca falha por isso, so grava `None` no que nao veio (ver
    # `XOAuthClient.get_tweet_metrics`). `public_metrics` (like/reply/
    # repost/quote) e o piso confiavel, sempre esperado com `tweet.read`.
    impression_count: Mapped[int | None] = mapped_column(nullable=True)
    like_count: Mapped[int | None] = mapped_column(nullable=True)
    reply_count: Mapped[int | None] = mapped_column(nullable=True)
    repost_count: Mapped[int | None] = mapped_column(nullable=True)
    quote_count: Mapped[int | None] = mapped_column(nullable=True)

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    post_account: Mapped["PostAccount"] = relationship()
    twitter_account: Mapped["TwitterAccount"] = relationship()

    def __repr__(self) -> str:
        return f"<PostMetricSnapshot post_account_id={self.post_account_id} collected_at={self.collected_at}>"
