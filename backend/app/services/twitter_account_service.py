"""Service de contas do X conectadas ao XHub."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from app.core.crypto import decrypt_token, encrypt_token
from app.models.twitter_account import TwitterAccount
from app.repositories.twitter_account_repository import TwitterAccountRepository
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService, NotFoundError


class TwitterAccountService(BaseService[TwitterAccount]):
    def __init__(
        self,
        twitter_account_repository: TwitterAccountRepository,
        user_repository: UserRepository,
    ) -> None:
        super().__init__(twitter_account_repository)
        self.twitter_account_repository = twitter_account_repository
        self.user_repository = user_repository

    def list_user_accounts(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 100
    ) -> Sequence[TwitterAccount]:
        self._ensure_user_exists(user_id)
        return self.twitter_account_repository.list_by_user(
            user_id, offset=offset, limit=limit
        )

    def get_user_account(
        self, user_id: uuid.UUID, twitter_user_id: str
    ) -> TwitterAccount | None:
        self._ensure_user_exists(user_id)
        return self.twitter_account_repository.get_by_user_and_twitter_user_id(
            user_id, twitter_user_id
        )

    def connect_account(self, user_id: uuid.UUID) -> TwitterAccount:
        self._ensure_user_exists(user_id)
        self.not_implemented("Conexao OAuth com o X")

    def save_connected_account(
        self,
        *,
        user_id: uuid.UUID,
        twitter_user_id: str,
        username: str,
        display_name: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
    ) -> TwitterAccount:
        self._ensure_user_exists(user_id)
        account = self.twitter_account_repository.get_by_user_and_twitter_user_id(
            user_id,
            twitter_user_id,
        )
        data = {
            "user_id": user_id,
            "twitter_user_id": twitter_user_id,
            "username": username,
            "display_name": display_name,
            # Tokens do OAuth do X sao cifrados (Fernet, autenticado)
            # antes de tocar o banco -- nunca persistir em texto puro.
            "access_token": encrypt_token(access_token),
            "refresh_token": encrypt_token(refresh_token),
            "expires_at": expires_at,
        }

        if account is None:
            return self.twitter_account_repository.create(data)

        return self.twitter_account_repository.update(account, data)

    def get_decrypted_access_token(self, account: TwitterAccount) -> str:
        """Descriptografa o access_token de uma conta para uso em
        chamadas a API do X. Nunca expor o valor cifrado nem o
        decifrado fora da camada de service."""
        return decrypt_token(account.access_token)

    def get_decrypted_refresh_token(self, account: TwitterAccount) -> str:
        return decrypt_token(account.refresh_token)

    def disconnect_account(self, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
        self._ensure_user_exists(user_id)
        account = self.twitter_account_repository.get(account_id)
        if account is None or account.user_id != user_id:
            raise NotFoundError("Conta do X nao encontrada para este usuario.")

        self.twitter_account_repository.delete(account)

    def _ensure_user_exists(self, user_id: uuid.UUID) -> None:
        if self.user_repository.get(user_id) is None:
            raise NotFoundError("Usuario nao encontrado.")
