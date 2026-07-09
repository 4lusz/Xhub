"""Model RefreshToken -- permite renovar o access token JWT sem exigir
novo login por senha a cada expiracao.

Correcao (auditoria item 11): `JWT_REFRESH_TOKEN_EXPIRE_DAYS` ja existia
em `Settings`, mas nunca era usado -- nao havia `/auth/refresh` nem
nenhuma emissao de refresh token. O access token durava 30 minutos e,
ao expirar, o unico caminho era fazer login com senha novamente. Este
model persiste o refresh token como HASH (SHA-256, ver
`app.auth.refresh_token`), nunca em texto puro -- mesma logica de nao
guardar senhas em claro -- para que um vazamento do banco nao exponha
tokens de sessao validos.

Rotacao (refresh token rotation): a cada uso, o token e revogado
(`revoked_at` preenchido) e um novo e emitido (ver
`AuthService.rotate_refresh_token`). Isso limita o dano de um token
vazado: assim que o dono legitimo o usar novamente, o uso do token
vazado (agora revogado) falha, sinalizando comprometimento.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id}>"
