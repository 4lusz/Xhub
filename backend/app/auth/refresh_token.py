"""Geracao e hashing de refresh tokens opacos.

O refresh token entregue ao cliente e um valor aleatorio opaco (nao um
JWT) -- nao carrega nenhuma informacao decodificavel, apenas serve como
uma chave de busca para o registro correspondente em `refresh_tokens`
(guardado como hash, nunca em texto puro, ver `app.models.refresh_token`).
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from app.config.settings import settings


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
