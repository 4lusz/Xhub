"""Model RevokedAccessToken -- denylist minima de access tokens JWT revogados.

Ver `app.auth.jwt` (claim `jti`) e `app.repositories.revoked_access_token_repository`.
Sem `TimestampMixin`: o registro nunca e atualizado apos criado, so
consultado (`is_revoked`) ou apagado quando o token que ele representa
ja teria expirado de qualquer forma (`delete_expired`).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class RevokedAccessToken(Base):
    __tablename__ = "revoked_access_tokens"

    jti: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RevokedAccessToken jti={self.jti}>"
