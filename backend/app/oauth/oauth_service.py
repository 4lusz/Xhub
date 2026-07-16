"""Service de orquestracao do OAuth 2.0 Authorization Code Flow com PKCE."""

import uuid
from datetime import UTC, datetime, timedelta

from app.core.exceptions import BadRequestException, UnauthorizedException
from app.models.oauth_session import OAuthSession
from app.models.twitter_account import TwitterAccount
from app.oauth.oauth_client import XOAuthClient
from app.oauth.pkce import generate_code_challenge, generate_code_verifier, generate_state
from app.repositories.oauth_session_repository import OAuthSessionRepository
from app.services.twitter_account_service import TwitterAccountService
from app.services.subscription_service import SubscriptionService


class XOAuthService:
    # TTL da sessao de login PKCE: tempo maximo que o usuario tem, apos
    # clicar em "conectar conta do X", para concluir a autorizacao no X
    # e retornar ao callback.
    _session_ttl = timedelta(minutes=10)

    def __init__(
        self,
        *,
        oauth_client: XOAuthClient,
        twitter_account_service: TwitterAccountService,
        subscription_service: SubscriptionService,
        oauth_session_repository: OAuthSessionRepository,
    ) -> None:
        self.oauth_client = oauth_client
        self.twitter_account_service = twitter_account_service
        self.subscription_service = subscription_service
        self.oauth_session_repository = oauth_session_repository

    def build_login_url(self, user_id: uuid.UUID) -> str:
        self.subscription_service.ensure_can_connect_account(user_id, for_update=True)

        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        state = generate_state()
        now = datetime.now(UTC)

        # Limpeza oportunista de sessoes expiradas e nunca consumidas
        # (usuario abandonou o fluxo). Nao e critico para a correcao,
        # apenas evita acumulo indefinido de linhas na tabela.
        self.oauth_session_repository.delete_expired(before=now)

        self.oauth_session_repository.create(
            {
                "state": state,
                "user_id": user_id,
                "code_verifier": code_verifier,
                "expires_at": now + self._session_ttl,
            }
        )

        return self.oauth_client.build_authorization_url(
            state=state,
            code_challenge=code_challenge,
        )

    def complete_callback(self, *, state: str, code: str) -> TwitterAccount:
        session = self._consume_session(state)
        tokens = self.oauth_client.exchange_code_for_tokens(
            code=code,
            code_verifier=session.code_verifier,
        )
        profile = self.oauth_client.get_authenticated_user(tokens.access_token)
        existing_account = self.twitter_account_service.get_user_account(
            session.user_id,
            profile.twitter_user_id,
        )
        if existing_account is None:
            self.subscription_service.ensure_can_connect_account(
                session.user_id,
                for_update=True,
            )

        return self.twitter_account_service.save_connected_account(
            user_id=session.user_id,
            twitter_user_id=profile.twitter_user_id,
            username=profile.username,
            display_name=profile.display_name,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_at=tokens.expires_at,
            profile_image_url=profile.profile_image_url,
        )

    def _consume_session(self, state: str) -> OAuthSession:
        if not state:
            raise BadRequestException("State ausente.")

        session = self.oauth_session_repository.get_by_state(state)
        if session is None:
            raise UnauthorizedException("State invalido ou expirado.")

        # Uso unico: a sessao e removida assim que lida, esteja ela
        # expirada ou nao, para que o mesmo `state` nunca possa ser
        # reaproveitado (protecao contra replay do callback).
        self.oauth_session_repository.delete(session)

        if session.expires_at < datetime.now(UTC):
            raise UnauthorizedException("State expirado.")

        return session
