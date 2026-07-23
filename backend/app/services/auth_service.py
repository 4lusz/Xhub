"""Service de autenticacao.

Correcao (auditoria item 11): implementa emissao, rotacao e revogacao
de refresh tokens (`JWT_REFRESH_TOKEN_EXPIRE_DAYS` ja existia em
`Settings` mas nunca era usado). Ver `app.models.refresh_token` e
`app.auth.refresh_token` para detalhes de armazenamento/seguranca.
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.auth.jwt import create_access_token, decode_access_token
from app.auth.password import hash_password, verify_password
from app.auth.refresh_token import (
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.domain.security_answer import normalize_security_answer
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.revoked_access_token_repository import (
    RevokedAccessTokenRepository,
)
from app.repositories.user_repository import UserRepository

# Segundo fator simples de login (pergunta de seguranca), hoje restrito
# a administradores -- ver docs/AUDITORIA_SEGURANCA.md (auditoria
# pos-deploy 2026-07-22). O token "pendente" emitido apos senha correta
# (quando o usuario tem um segundo fator configurado) carrega a claim
# `stage=pending_2fa` e tem validade curta -- nunca deve ser aceito como
# token de acesso normal em nenhuma outra rota (ver bloqueio explicito
# em `app.auth.dependencies._resolve_authenticated_user`).
_PENDING_2FA_STAGE = "pending_2fa"
_PENDING_2FA_EXPIRE_MINUTES = 5

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
        revoked_access_token_repository: RevokedAccessTokenRepository | None = None,
    ) -> None:
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository
        # Opcional (auditoria de seguranca -- item 4, JWT): so
        # `get_auth_service` (producao) injeta de fato; testes que nao
        # exercitam revogacao de access token podem seguir montando
        # `AuthService` sem esse repository, sem quebrar.
        self.revoked_access_token_repository = revoked_access_token_repository

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

    def requires_second_factor(self, user: User) -> bool:
        """`True` somente quando o usuario configurou uma pergunta de
        seguranca (ver `UserService.set_security_question`) -- opcional
        por design, nunca bloqueia quem ainda nao configurou."""
        return user.security_question is not None and user.security_answer_hash is not None

    def issue_pending_2fa_token(self, user: User) -> str:
        """Emitido no lugar do par access+refresh normal quando o login
        (email+senha) e valido mas o usuario exige segundo fator.
        Validade curta de proposito -- so serve para
        `verify_security_answer` completar o login, nunca para acessar
        qualquer outra rota."""
        return create_access_token(
            str(user.id),
            expires_delta=timedelta(minutes=_PENDING_2FA_EXPIRE_MINUTES),
            extra_claims={"stage": _PENDING_2FA_STAGE},
        )

    def verify_security_answer(self, *, pending_token: str, answer: str) -> User:
        """Completa o login em duas etapas: valida o token pendente
        (emitido por `issue_pending_2fa_token` apos senha correta) e a
        resposta da pergunta de seguranca. Retorna o usuario -- a rota
        emite o par de tokens normal (access + refresh) a partir daqui,
        exatamente como um login comum bem sucedido."""
        try:
            payload = decode_access_token(pending_token)
        except UnauthorizedException as exc:
            raise UnauthorizedException(
                "Sessao de verificacao invalida ou expirada. Faca login novamente."
            ) from exc

        if payload.get("stage") != _PENDING_2FA_STAGE:
            raise UnauthorizedException("Sessao de verificacao invalida.")

        user = self.user_repository.get(uuid.UUID(payload["sub"]))
        if user is None:
            raise UnauthorizedException("Sessao de verificacao invalida.")

        if user.is_blocked:
            raise ForbiddenException("Usuario bloqueado.")

        if not self.requires_second_factor(user):
            # Segundo fator foi removido entre a senha e esta etapa
            # (ex.: admin desativou a pergunta em outra aba) -- trata
            # como sessao de verificacao invalida, nunca aceita sem
            # checagem.
            raise UnauthorizedException("Sessao de verificacao invalida.")

        if not verify_password(
            normalize_security_answer(answer), user.security_answer_hash
        ):
            raise UnauthorizedException("Resposta de seguranca incorreta.")

        return user

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

    def revoke_access_token(self, access_token: str) -> None:
        """Revoga o access token JWT em uso (auditoria de seguranca --
        item 4, JWT: "um token usado apos logout deve retornar 401").

        Silenciosamente ignora tokens ja invalidos/expirados/malformados
        -- nesse caso ja nao ha nada de fato revogavel (um token expirado
        e rejeitado por `decode_access_token` de qualquer forma) e o
        logout nunca deve falhar por causa disso: revogar o refresh
        token (ver `revoke_refresh_token`) e sempre o efeito principal e
        garantido, a revogacao do access token e um reforco extra.
        """
        if self.revoked_access_token_repository is None:
            return

        try:
            payload = decode_access_token(access_token)
        except UnauthorizedException:
            return

        jti = payload.get("jti")
        expires_at_timestamp = payload.get("exp")
        if not jti or expires_at_timestamp is None:
            return

        self.revoked_access_token_repository.revoke(
            uuid.UUID(jti),
            datetime.fromtimestamp(expires_at_timestamp, tz=UTC),
        )
        self.revoked_access_token_repository.delete_expired(datetime.now(UTC))
