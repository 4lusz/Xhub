"""
Base declarativa do SQLAlchemy 2.0.

Todos os models devem herdar de `Base`. O Alembic importa este modulo
(via app.models) para gerar as migrations automaticamente.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa compartilhada por todos os models."""
    pass


class TimestampMixin:
    """Mixin que adiciona created_at/updated_at automaticamente."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
