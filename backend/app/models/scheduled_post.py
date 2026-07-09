"""Model ScheduledPost -- agendamento de publicacao de um Post."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.post import Post


class ScheduledPost(TimestampMixin, Base):
    __tablename__ = "scheduled_posts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # unique=True -> um Post tem no maximo um agendamento (1:1).
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # `executed=True` significa que o worker ja tentou processar este
    # agendamento (sucesso ou falha) -- nao e reprocessado novamente.
    # O resultado da tentativa fica no status do `Post`/`PostAccount`
    # associado (ver `PostService.publish_post`) e em `last_error`
    # abaixo, quando a tentativa falhou de forma inesperada.
    executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    post: Mapped["Post"] = relationship(back_populates="scheduled_post")

    def __repr__(self) -> str:
        return f"<ScheduledPost id={self.id} scheduled_for={self.scheduled_for} executed={self.executed}>"

