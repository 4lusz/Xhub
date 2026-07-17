"""Service de autenticacao.

Correcao (auditoria item 11): implementa emissao, rotacao e revogacao
de refresh tokens (`JWT_REFRESH_TOKEN_EXPIRE_DAYS` ja existia em
`Settings` mas nunca era usado). Ver `app.models.refresh_token` e
`app.auth.refresh_token` para detalhes de armazenamento/seguranca.
"""

from datetime import UTC, datetime

from app.auth.jwt import create_access_token
from app.auth.password import hash_password, verify_password
from app.auth.refresh_token import (
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository

# Correcao (auditoria de seguranca -- enumeracao de usuarios via timing):
# quando o e-mail nao existe, `authenticate` abaixo nunca chamava
# `verify_password` (bcrypt e deliberadamente lento, ~100ms), tornando a
# resposta a um e-mail inexistente mensuravelmente mais RAPIDA do que a
# um e-mail existente com senha errada -- um atacante podia enumerar
# e-mails cadastrados so medindo o tempo de resposta de `/auth/login`,
# mesmo a mensagem de erro sendo identica nos dois casos. Um hash bcrypt
# "isca" (calculado uma unica vez, no import deste modulo) e verificado
# mesmo quando o usuario nao existe, para que o custo computacional da
# resposta seja o mesmo nos dois casos.
_TIMING_MITIGATION_DUMMY_HASH = hash_password("xhub-timing-mitigation-dummy-password")


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

        if user is None:
            # Mesmo custo computacional de uma verificacao real (ver
            # `_TIMING_MITIGATION_DUMMY_HASH`) -- nunca retorna mais
            # rapido so por o e-mail nao existir.
            verify_password(password, _TIMING_MITIGATION_DUMMY_HASH)
            raise UnauthorizedException("Email ou senha invalidos.")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedException("Email ou senha invalidos.")

        # Correcao (auditoria funcional): bloqueio de CONTA (ver
        # `app.domain.policies.ensure_user_not_blocked`, cujo proprio
        # docstring ja documentava esta regra: "usuario nao pode logar
        # nem realizar nenhuma acao") nao era checado aqui -- um usuario
        # bloqueado conseguia concluir login normalmente e receber um
        # par de tokens validos, so esbarrando no bloqueio na PROXIMA
        # requisicao (`get_current_user`/`ensure_user_not_blocked`).
        # `rotate_refresh_token` abaixo ja fazia essa checagem para
        # renovacao de sessao; login ficava inconsistente por omissao.
        # Mesma excecao/mensagem usada em toda a aplicacao para bloqueio
        # de conta, para que o frontend trate o caso de forma uniforme
        # nao importa por qual rota ele foi encontrado.
        if user.is_blocked:
            raise ForbiddenException("Usuario bloqueado.")

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
        if user is None:
            raise UnauthorizedException("Refresh token invalido.")

        # Mesma correcao de consistencia do bloqueio de conta: mensagem
        # e excecao identicas as usadas em login/qualquer rota protegida
        # (`ForbiddenException`/"Usuario bloqueado."), em vez da mensagem
        # generica anterior que misturava "nao encontrado" com
        # "bloqueado" sob o mesmo 401 -- o frontend nao conseguia
        # distinguir os dois casos por esta rota.
        if user.is_blocked:
            raise ForbiddenException("Usuario bloqueado.")

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
