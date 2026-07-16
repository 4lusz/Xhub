"""Utilitarios para hash e verificacao de senha."""

import secrets

from passlib.context import CryptContext

from app.core.exceptions import ValidationException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
BCRYPT_MAX_PASSWORD_BYTES = 72

# Tamanho da senha temporaria gerada em `generate_temporary_password`
# (ver docs/ROADMAP_PRIMEIRO_ACESSO.md, redefinicao administrativa) --
# suficiente para ser segura mesmo sendo exibida uma unica vez ao
# administrador e comunicada manualmente ao cliente.
_TEMPORARY_PASSWORD_LENGTH = 16


def validate_password_for_bcrypt(password: str) -> None:
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValidationException(
            "Senha excede o limite de 72 bytes suportado pelo bcrypt."
        )


def hash_password(password: str) -> str:
    validate_password_for_bcrypt(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    validate_password_for_bcrypt(plain_password)
    return pwd_context.verify(plain_password, password_hash)


# Alfabeto sem caracteres ambiguos (sem 0/O, 1/l/I) -- a senha e
# comunicada manualmente pelo administrador ao cliente (voz, chat,
# etc.), entao facilidade de leitura/digitacao importa tanto quanto
# entropia.
_TEMPORARY_PASSWORD_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def generate_temporary_password() -> str:
    """Gera uma senha temporaria aleatoria e criptograficamente segura
    (ver docs/ROADMAP_PRIMEIRO_ACESSO.md, redefinicao administrativa).
    Retornada em texto puro APENAS na resposta HTTP da redefinicao --
    nunca persistida (so o hash, via `hash_password`) nem registrada em
    log/auditoria."""
    return "".join(
        secrets.choice(_TEMPORARY_PASSWORD_ALPHABET)
        for _ in range(_TEMPORARY_PASSWORD_LENGTH)
    )
