"""Model OAuthSession -- estado do fluxo OAuth2/PKCE do X entre o
/oauth/x/login e o /oauth/x/callback.

Correcao critica: antes, esse estado (state + code_verifier) ficava em
um dict Python em memoria (`XOAuthService._sessions`), que so funciona
em um unico processo. Persistindo em banco, o fluxo funciona
corretamente com multiplos workers/replicas da aplicacao, ja que
qualquer processo pode ler o registro gravado por outro.

Nao referencia `TwitterAccount` de proposito: e apenas um registro
efemero e de uso unico (consumido e apagado no callback), nao faz parte
do historico de dominio.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class OAuthSession(TimestampMixin, Base):
    __tablename__ = "oauth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # `state` do OAuth2 -- valor unico e imprevisivel usado para casar
    # o callback com a sessao de login que o originou (protecao CSRF do
    # fluxo OAuth). Indexado e unico: cada login gera um state novo.
    state: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # PKCE code_verifier -- efemero (TTL curto, uso unico) e nao e, por
    # si so, uma credencial de acesso a conta do X (apenas prova de
    # posse do lado que iniciou o authorization request), por isso nao
    # e cifrado como os tokens de acesso/refresh do X.
    code_verifier: Mapped[str] = mapped_column(String(255), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<OAuthSession id={self.id} user_id={self.user_id}>"
