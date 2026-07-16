"""Model TwitterAccount -- uma conta do X (Twitter) conectada via OAuth2."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.post_account import PostAccount
    from app.models.user import User


class TwitterAccount(TimestampMixin, Base):
    __tablename__ = "twitter_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "twitter_user_id", name="uq_user_twitter_account"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    twitter_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # URL publica da foto de perfil no X (`profile_image_url` retornado
    # por `GET /2/users/me`, ja em resolucao maior -- ver
    # `XOAuthClient._parse_user`). NULL para contas conectadas antes
    # desta funcionalidade, ate que sejam reconectadas; o frontend usa
    # as iniciais do nome como fallback nesse caso.
    profile_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Tokens do OAuth2 do X. Nesta etapa (models) sao colunas de texto puro.
    # A etapa de OAuth/seguranca deve adicionar criptografia em repouso
    # (ex.: Fernet) antes de qualquer token real ser persistido em producao.
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    refresh_token: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(back_populates="twitter_accounts")
    post_accounts: Mapped[list["PostAccount"]] = relationship(
        back_populates="twitter_account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TwitterAccount id={self.id} username={self.username!r}>"
