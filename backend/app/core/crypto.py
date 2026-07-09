"""Criptografia simetrica autenticada para segredos em repouso.

Usado para cifrar `access_token`/`refresh_token` do OAuth2 do X antes de
persistir no banco (`TwitterAccount`). Usa Fernet (biblioteca
`cryptography`), que combina AES-128 em modo CBC com autenticacao
HMAC-SHA256 -- ou seja, criptografia simetrica *autenticada*: qualquer
adulteracao do texto cifrado e detectada na descriptografia
(`InvalidToken`), nao apenas encoding/hash.

A chave vem exclusivamente de `settings.TOKEN_ENCRYPTION_KEY` (variavel
de ambiente) -- nunca gerada ou derivada localmente.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import settings
from app.core.exceptions import UnauthorizedException

# Prefixo gravado em todo valor cifrado por esta versao do esquema.
# Permite detectar de forma explicita um token que NAO foi cifrado por
# este modulo (ex.: token legado gravado em texto puro antes desta
# correcao), em vez de falhar de forma obscura tentando descriptografar
# texto arbitrario.
_CIPHERTEXT_PREFIX = "fernet:v1:"


class TokenDecryptionError(UnauthorizedException):
    """Levantado quando um valor armazenado nao pode ser descriptografado.

    Cobre tanto adulteracao/corrupcao do dado quanto tokens legados
    gravados em texto puro antes da criptografia ser introduzida --
    nesses dois casos a unica acao segura e pedir para o usuario
    reconectar a conta do X.
    """

    default_message = (
        "Nao foi possivel descriptografar o token armazenado. "
        "Reconecte a conta do X."
    )
    default_code = "token_decryption_error"


def _fernet() -> Fernet:
    try:
        return Fernet(settings.TOKEN_ENCRYPTION_KEY.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY invalido: deve ser uma chave Fernet de "
            "32 bytes codificada em urlsafe-base64 (gerar com "
            "`Fernet.generate_key()`)."
        ) from exc


def encrypt_token(plain_value: str) -> str:
    """Cifra um valor sensivel (ex.: access_token/refresh_token do X)."""
    if not plain_value:
        raise ValueError("plain_value nao pode ser vazio.")

    token = _fernet().encrypt(plain_value.encode("utf-8")).decode("ascii")
    return f"{_CIPHERTEXT_PREFIX}{token}"


def decrypt_token(stored_value: str) -> str:
    """Descriptografa um valor previamente cifrado por `encrypt_token`.

    Levanta `TokenDecryptionError` (nunca uma excecao de baixo nivel da
    lib de criptografia) tanto para dado corrompido/adulterado quanto
    para valores legados sem o prefixo esperado (texto puro anterior a
    esta correcao).
    """
    if not stored_value or not stored_value.startswith(_CIPHERTEXT_PREFIX):
        raise TokenDecryptionError(
            "Token armazenado em formato legado (nao cifrado) ou "
            "invalido. Reconecte a conta do X."
        )

    ciphertext = stored_value[len(_CIPHERTEXT_PREFIX):]

    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenDecryptionError(
            "Token armazenado corrompido ou cifrado com uma chave "
            "diferente da atual. Reconecte a conta do X."
        ) from exc
