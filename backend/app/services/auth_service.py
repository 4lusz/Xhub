"""Service de autenticacao.

Correcao (auditoria item 11): implementa emissao, rotacao e revogacao
de refresh tokens (`JWT_REFRESH_TOKEN_EXPIRE_DAYS` ja existia em
`Settings` mas nunca era usado). Ver `app.models.refresh_token` e
`app.auth.refresh_token` para detalhes de armazenamento/seguranca.
"""

from datetime import UTC, datetime

from app.auth.jwt import create_access_token
from app.auth.password import verify_password
from app.auth.refresh_token import (
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.core.exceptions import UnauthorizedException
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

    def authenticate(self, *, email: str, password: str) -> User:
        user = self.user_repository.get_by_email(email.strip().lower())
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Email ou senha invalidos.")

        return user

    def create_access_token(self, user: User) -> str:
        return create_access_token(str(user.id))

    def issue_refresh_token(self, user: User) -> str:
        raw_token = generate_refresh_token()
        self.refresh_token_repository.create(
            {
                "user_id": user.id,
                "token_hash": hash_refresh_token(raw_token),
                "expires_at": refresh_token_expiry(),
                "revoked_at": None,
            }
        )
        return raw_token

    def rotate_refresh_token(self, raw_token: str) -> tuple[User, str]:
        """Valida um refresh token e emite um novo par (access +
        refresh). O token usado e revogado (uso unico): se o mesmo
        token opaco for apresentado novamente, sera rejeitado --
        limitando o dano de um token vazado e permitindo detectar reuso
        indevido."""
        stored = self.refresh_token_repository.get_by_hash(
            hash_refresh_token(raw_token)
        )

        if stored is None or stored.revoked_at is not None:
            raise UnauthorizedException("Refresh token invalido.")

        expires_at = stored.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            raise UnauthorizedException("Refresh token expirado.")

        user = self.user_repository.get(stored.user_id)
        if user is None or user.is_blocked:
            raise UnauthorizedException("Usuario nao encontrado ou bloqueado.")

        self.refresh_token_repository.update(
            stored, {"revoked_at": datetime.now(UTC)}
        )

        new_raw_token = self.issue_refresh_token(user)
        return user, new_raw_token

    def revoke_refresh_token(self, raw_token: str) -> None:
        stored = self.refresh_token_repository.get_by_hash(
            hash_refresh_token(raw_token)
        )
        if stored is not None and stored.revoked_at is None:
            self.refresh_token_repository.update(
                stored, {"revoked_at": datetime.now(UTC)}
            )
