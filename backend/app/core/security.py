"""Utilitarios de seguranca sem autenticacao acoplada."""

import hmac
import secrets
import string
import uuid

DEFAULT_RANDOM_STRING_ALPHABET = string.ascii_letters + string.digits


def generate_secure_token(length: int = 32) -> str:
    """Gera um token URL-safe usando entropia criptografica."""
    return secrets.token_urlsafe(length)


def generate_hex_token(length: int = 32) -> str:
    """Gera um token hexadecimal usando entropia criptografica."""
    return secrets.token_hex(length)


def generate_random_string(
    length: int = 32,
    *,
    alphabet: str = DEFAULT_RANDOM_STRING_ALPHABET,
) -> str:
    if length <= 0:
        raise ValueError("length deve ser maior que zero.")
    if not alphabet:
        raise ValueError("alphabet nao pode ser vazio.")

    return "".join(secrets.choice(alphabet) for _ in range(length))


def secure_compare(value: str, expected: str) -> bool:
    """Compara strings em tempo constante."""
    return hmac.compare_digest(value, expected)


def generate_uuid() -> uuid.UUID:
    return uuid.uuid4()


def generate_uuid_str() -> str:
    return str(generate_uuid())


def is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False

    return True
