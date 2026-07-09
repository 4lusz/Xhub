"""Model User -- dono da conta no XHub (nao confundir com conta do X/Twitter)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.subscription import Subscription
    from app.models.twitter_account import TwitterAccount


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    # Nunca armazenamos a senha do X aqui -- apenas o hash da senha de
    # cadastro do proprio XHub (bcrypt, ver etapa de autenticacao).
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role", native_enum=True),
        nullable=False,
        default=UserRole.CLIENT,
    )
    # Bloqueio de CONTA (ex.: fraude, abuso, decisao administrativa sobre o
    # usuario em si) -- impede login e qualquer acao no XHub, independente
    # do estado da assinatura. Nao confundir com o bloqueio de ASSINATURA
    # (`Subscription.status == BLOCKED`), que restringe apenas o uso do
    # plano (consumo de posts, conexao de contas) mas nao impede o login.
    # Ver `app.domain.policies.ensure_user_not_blocked` vs.
    # `ensure_subscription_active`.
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    twitter_accounts: Mapped[list["TwitterAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    posts: Mapped[list["Post"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
