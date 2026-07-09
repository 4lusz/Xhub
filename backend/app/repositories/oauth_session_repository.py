"""Repository para o model OAuthSession."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oauth_session import OAuthSession
from app.repositories.base import BaseRepository


class OAuthSessionRepository(BaseRepository[OAuthSession]):
    """Acesso a dados das sessoes efemeras de OAuth2/PKCE do X."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, OAuthSession)

    def get_by_state(self, state: str) -> OAuthSession | None:
        statement = select(OAuthSession).where(OAuthSession.state == state)
        return self.db.scalars(statement).first()

    def delete_expired(self, *, before: datetime) -> None:
        """Remove sessoes expiradas e nunca consumidas (limpeza
        oportunista, chamada ao criar uma nova sessao)."""
        statement = select(OAuthSession).where(OAuthSession.expires_at < before)
        for session in self.db.scalars(statement).all():
            self.db.delete(session)
        self.db.flush()
