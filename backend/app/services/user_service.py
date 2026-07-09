"""Service de usuarios do XHub."""

import re
import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError

from app.auth.password import hash_password
from app.core.exceptions import ConflictException, ValidationException
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService, NotFoundError

# Validacao pragmatica de formato de e-mail (nao substitui confirmacao
# por e-mail, que nao faz parte do escopo atual). Cobre os casos que a
# checagem anterior (apenas `"@" in email`) deixava passar, como
# "a@b", "@dominio.com" ou "usuario@dominio" sem TLD.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserService(BaseService[User]):
    def __init__(self, user_repository: UserRepository) -> None:
        super().__init__(user_repository)
        self.user_repository = user_repository

    def get_user(self, user_id: uuid.UUID) -> User | None:
        return self.user_repository.get(user_id)

    def list_users(self, *, offset: int = 0, limit: int = 100) -> Sequence[User]:
        return self.user_repository.list(offset=offset, limit=limit)

    def get_by_email(self, email: str) -> User | None:
        return self.user_repository.get_by_email(email)

    def ensure_email_available(self, email: str) -> None:
        if self.user_repository.email_exists(email):
            raise ConflictException("Email ja cadastrado.")

    def create_user(
        self,
        *,
        name: str,
        email: str,
        password: str,
        role: UserRole = UserRole.CLIENT,
    ) -> User:
        normalized_email = self._normalize_email(email)
        self._validate_name(name)
        self._validate_password(password)
        self.ensure_email_available(normalized_email)

        try:
            return self.user_repository.create(
                {
                    "name": name.strip(),
                    "email": normalized_email,
                    "password_hash": hash_password(password),
                    "role": role,
                }
            )
        except IntegrityError as exc:
            # Corrige corrida de cadastro duplicado (auditoria item 9):
            # o check `ensure_email_available` acima e o INSERT nao sao
            # atomicos, entao duas requisicoes concorrentes com o mesmo
            # e-mail podem passar pela validacao antes de qualquer uma
            # commitar. A constraint UNIQUE do banco e quem realmente
            # impede o duplicado -- mas o erro chega aqui como
            # `IntegrityError` do SQLAlchemy, que nao e um
            # `BaseAppException` e portanto nao seria capturado pelo
            # `except BaseAppException` das rotas, resultando em 500
            # generico em vez do 409 esperado. Convertemos explicitamente
            # para `ConflictException` e desfazemos a insercao invalida
            # da sessao para nao deixar a transacao "suja".
            self.user_repository.db.rollback()
            raise ConflictException("Email ja cadastrado.") from exc

    def block_user(self, user_id: uuid.UUID) -> User:
        user = self._ensure_user_exists(user_id)
        return self.user_repository.update(user, {"is_blocked": True})

    def unblock_user(self, user_id: uuid.UUID) -> User:
        user = self._ensure_user_exists(user_id)
        return self.user_repository.update(user, {"is_blocked": False})

    def change_role(self, user_id: uuid.UUID, role: UserRole) -> User:
        user = self._ensure_user_exists(user_id)
        return self.user_repository.update(user, {"role": role})

    def _normalize_email(self, email: str) -> str:
        normalized = email.strip().lower()
        if not _EMAIL_PATTERN.match(normalized):
            raise ValidationException("Email invalido.")
        return normalized

    def _validate_name(self, name: str) -> None:
        if not name.strip():
            raise ValidationException("Nome e obrigatorio.")

    def _validate_password(self, password: str) -> None:
        if len(password) < 8:
            raise ValidationException("Senha deve ter pelo menos 8 caracteres.")

    def _ensure_user_exists(self, user_id: uuid.UUID) -> User:
        user = self.user_repository.get(user_id)
        if user is None:
            raise NotFoundError("Usuario nao encontrado.")
        return user

