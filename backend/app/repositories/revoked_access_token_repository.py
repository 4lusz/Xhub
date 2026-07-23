"""Repository para o model RevokedAccessToken (denylist de JWT)."""

import uuid
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.revoked_access_token import RevokedAccessToken
from app.repositories.base import BaseRepository


class RevokedAccessTokenRepository(BaseRepository[RevokedAccessToken]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, RevokedAccessToken)

    def is_revoked(self, jti: uuid.UUID) -> bool:
        return self.get(jti) is not None

    def revoke(self, jti: uuid.UUID, expires_at: datetime) -> None:
        """Registra `jti` como revogado. Idempotente -- revogar duas
        vezes o mesmo token (ex.: logout chamado duas vezes) nao gera
        erro nem linha duplicada."""
        if self.is_revoked(jti):
            return
        self.create({"jti": jti, "expires_at": expires_at})

    def delete_expired(self, now: datetime) -> int:
        """Remove entradas cujo token ja expiraria de qualquer forma --
        chamado a cada nova revogacao (ver `AuthService.revoke_access_token`)
        para manter a tabela pequena sem exigir um job dedicado, ja que
        access tokens tem vida curta (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)."""
        result = self.db.execute(
            delete(RevokedAccessToken).where(RevokedAccessToken.expires_at < now)
        )
        return result.rowcount or 0
