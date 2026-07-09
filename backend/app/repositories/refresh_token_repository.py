"""Repository para o model RefreshToken."""

from sqlalchemy import select
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
