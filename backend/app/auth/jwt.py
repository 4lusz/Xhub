"""Geracao e validacao de access tokens JWT."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.config.settings import settings
from app.core.exceptions import UnauthorizedException


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    expires_at = datetime.now(UTC) + (
        expires_delta
        or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    # `jti` (auditoria de seguranca -- item 4, JWT): identificador unico
    # por token, necessario para revogar um access token especifico no
    # logout sem precisar manter estado de todas as sessoes ativas (ver
    # `app.repositories.revoked_access_token_repository`).
    payload: dict[str, Any] = {"sub": subject, "exp": expires_at, "jti": str(uuid.uuid4())}
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise UnauthorizedException("Token invalido ou expirado.") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise UnauthorizedException("Token invalido.")

    return payload
