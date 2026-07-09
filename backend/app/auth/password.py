"""Utilitarios para hash e verificacao de senha."""

from passlib.context import CryptContext

from app.core.exceptions import ValidationException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
BCRYPT_MAX_PASSWORD_BYTES = 72


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
