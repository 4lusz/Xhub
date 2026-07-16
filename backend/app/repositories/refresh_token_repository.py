"""Repository para o model RefreshToken."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Acesso a dados dos refresh tokens de sessao."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, RefreshToken)

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.db.scalars(statement).first()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoga todas as sessoes ativas (refresh tokens ainda nao
        revogados) de um usuario -- usado na redefinicao administrativa
        de senha (ver docs/ROADMAP_PRIMEIRO_ACESSO.md): a senha
        temporaria so deve valer a partir de um novo login, nunca
        permitindo que uma sessao antiga continue renovando o access
        token sem passar pelo primeiro acesso obrigatorio."""
        statement = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        self.db.execute(statement)
        self.db.flush()
