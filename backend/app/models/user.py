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

    # Primeiro acesso obrigatorio (ver docs/ROADMAP_PRIMEIRO_ACESSO.md):
    # `True` enquanto `password_hash` guarda uma senha TEMPORARIA
    # (definida pelo administrador na criacao da conta ou em uma
    # redefinicao via `POST /admin/users/{id}/reset-password`) -- todo
    # usuario novo comeca com `True`. `POST /auth/change-password` e a
    # UNICA rota protegida acessivel enquanto este campo for `True`
    # (ver `app.auth.dependencies.get_current_user`); ao concluir a
    # troca, o campo volta a `False` e o acesso normal e liberado.
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Segundo fator simples de login, hoje restrito a administradores
    # (ver docs/AUDITORIA_SEGURANCA.md, auditoria pos-deploy 2026-07-22
    # -- conta com controle total sobre a plataforma, sem MFA de
    # verdade ate esta correcao). Opcional por design: `NULL` em ambas
    # colunas significa que o usuario nao configurou um segundo fator
    # ainda, e o login continua exigindo so email+senha para ele --
    # nunca bloqueia o acesso de um admin que ainda nao configurou.
    # `security_answer_hash` usa o mesmo esquema de `password_hash`
    # (bcrypt via `app.auth.password`), nunca texto puro.
    security_question: Mapped[str | None] = mapped_column(String(200), nullable=True)
    security_answer_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

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
